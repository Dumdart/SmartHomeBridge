import asyncio
import threading
import time

from smart_home_bridge.bridge_devices.chicken_door import (
    DoorStatePollingService,
    OPEN_DOOR_COMMAND,
    chicken_door,
    door_controller,
    door_position,
    door_status,
)


def test_polling_publishes_first_status_and_only_subsequent_changes():
    initial = door_status(
        door_position.CLOSED,
        battery_level=80,
        light_level=20,
        connected=True,
    )
    telemetry_change = door_status(
        door_position.CLOSED,
        battery_level=79,
        light_level=20,
        connected=True,
    )
    gateway = SequenceGateway([initial, initial, telemetry_change])
    published = []
    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=gateway,
        publishable=published.append,
    )
    service = DoorStatePollingService(controller, 5)

    async def scenario():
        await service.run_once()
        await service.run_once()
        await service.run_once()

    asyncio.run(scenario())

    assert published == [initial, telemetry_change]
    assert controller.device.position == door_position.CLOSED
    assert gateway.calls == ["get_state", "get_state", "get_state"]


def test_polling_failure_keeps_last_successful_comparison_status(caplog):
    status = door_status(door_position.OPEN, battery_level=65)
    gateway = SequenceGateway([status, RuntimeError("offline"), status])
    published = []
    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=gateway,
        publishable=published.append,
    )
    service = DoorStatePollingService(controller, 5)

    async def scenario():
        assert await service.run_once() == status
        assert await service.run_once() is None
        assert await service.run_once() == status

    asyncio.run(scenario())

    assert published == [status]
    assert "Door state poll failed" in caplog.text


def test_polling_retries_publication_after_mqtt_failure():
    status = door_status(door_position.CLOSED)
    gateway = SequenceGateway([status, status])
    published = []

    async def publish(current_status):
        if not published:
            published.append("failed")
            raise RuntimeError("mqtt unavailable")
        published.append(current_status)

    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=gateway,
        publishable=publish,
    )
    service = DoorStatePollingService(controller, 5)

    async def scenario():
        assert await service.run_once() is None
        assert await service.run_once() == status

    asyncio.run(scenario())

    assert published == ["failed", status]


def test_polling_does_not_emit_command_usage_events():
    usage_events = []
    status = door_status(door_position.OPEN)
    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=SequenceGateway([status]),
        publishable=lambda _status: None,
        usage_reporter=lambda *event: usage_events.append(event),
    )

    asyncio.run(DoorStatePollingService(controller, 5).run_once())

    assert usage_events == []


def test_polling_starts_immediately_and_stops_cleanly():
    called = threading.Event()
    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=SignalingGateway(called),
        publishable=lambda _status: None,
    )
    service = DoorStatePollingService(controller, 3600)

    async def scenario():
        await service.start()
        for _ in range(100):
            if called.is_set():
                break
            await asyncio.sleep(0.001)
        assert called.is_set()
        assert service.is_running is True
        await service.stop()
        assert service.is_running is False

    asyncio.run(scenario())


def test_gateway_calls_do_not_block_event_loop_and_are_serialized():
    gateway = ConcurrentGateway()
    controller = door_controller(
        chicken_door(1, "door", door_position.UNKNOWN),
        gateway=gateway,
        publishable=lambda _status: None,
    )
    event_loop_progressed = False

    async def mark_progress():
        nonlocal event_loop_progressed
        await asyncio.sleep(0.01)
        event_loop_progressed = True

    command_thread = threading.Thread(
        target=lambda: asyncio.run(
            controller.excecute_command(OPEN_DOOR_COMMAND),
        )
    )

    async def scenario():
        poll_task = asyncio.create_task(controller.poll_state(None))
        await asyncio.sleep(0.005)
        command_thread.start()
        await asyncio.gather(poll_task, mark_progress())

    asyncio.run(scenario())
    command_thread.join(timeout=1)

    assert event_loop_progressed is True
    assert command_thread.is_alive() is False
    assert gateway.maximum_concurrency == 1


class SequenceGateway:
    def __init__(self, results):
        self.results = iter(results)
        self.calls = []

    def get_state(self):
        self.calls.append("get_state")
        result = next(self.results)
        if isinstance(result, Exception):
            raise result
        return result


class SignalingGateway:
    def __init__(self, called):
        self.called = called

    def get_state(self):
        self.called.set()
        return door_status(door_position.CLOSED)


class ConcurrentGateway:
    def __init__(self):
        self.concurrency = 0
        self.maximum_concurrency = 0
        self._lock = threading.Lock()

    def get_state(self):
        return self._operate(door_status(door_position.CLOSED))

    def open(self):
        return self._operate(door_status(door_position.OPEN))

    def _operate(self, status):
        with self._lock:
            self.concurrency += 1
            self.maximum_concurrency = max(
                self.maximum_concurrency,
                self.concurrency,
            )
        time.sleep(0.05)
        with self._lock:
            self.concurrency -= 1
        return status
