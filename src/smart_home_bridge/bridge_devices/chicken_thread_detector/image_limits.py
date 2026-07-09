MAX_IMAGE_PIXELS = 4_000_000


def validate_image_size(image, max_pixels: int = MAX_IMAGE_PIXELS):
    width, height = image.size
    pixels = width * height
    if pixels > max_pixels:
        raise RuntimeError(f"Image exceeds {max_pixels} pixels: {width}x{height}")

__all__ = [
    "MAX_IMAGE_PIXELS",
    "validate_image_size",
]
