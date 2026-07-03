MAX_IMAGE_PIXELS = 4_000_000


def validate_image_size(image, max_pixels: int = MAX_IMAGE_PIXELS):
    width, height = image.size
    pixels = width * height
    if pixels > max_pixels:
        raise RuntimeError(
            f"Camera image exceeds {max_pixels} pixels: {width}x{height}"
        )
