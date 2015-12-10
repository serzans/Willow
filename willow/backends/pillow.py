from __future__ import absolute_import

from willow.utils import deprecation

import functools

from .base import ImageBackend


class PillowBackend(ImageBackend):
    def __init__(self, image):
        self.image = image

    def to_buffer(self):
        image = self.image

        if image.mode not in ['RGB', 'RGBA']:
            if 'A' in image.mode:
                image = image.convert('RGBA')
            else:
                image = image.convert('RGB')

        return image.mode, image.size, image.tobytes()

    @classmethod
    def from_buffer(cls, buf):
        mode, size, data = buf
        return cls(cls.get_pillow_image().frombytes(mode, size, data))

    def to_file(self, f):
        return self.image.save(f, 'PNG')

    @classmethod
    def from_file(cls, f):
        f.seek(0)
        image = cls.get_pillow_image().open(f)
        image.load()
        return cls(image)

    @classmethod
    def get_pillow_image(cls):
        import PIL.Image
        return PIL.Image

    @classmethod
    def check(cls):
        cls.get_pillow_image()


@PillowBackend.register_operation('get_size')
def get_size(backend):
    return backend.image.size


@PillowBackend.register_operation('resize')
@deprecation.deprecated_resize_parameters
def resize(backend, size):
    if backend.image.mode in ['1', 'P']:
        backend.image = backend.image.convert('RGB')

    backend.image = backend.image.resize(
        size, backend.get_pillow_image().ANTIALIAS)


@PillowBackend.register_operation('crop')
@deprecation.deprecated_crop_parameters
def crop(backend, rect):
    backend.image = backend.image.crop(rect)


@PillowBackend.register_operation('save_as_jpeg')
def save_as_jpeg(backend, f, quality=85):
    if backend.image.mode in ['1', 'P']:
        backend.image = backend.image.convert('RGB')

    backend.image.save(f, 'JPEG', quality=quality)


@PillowBackend.register_operation('save_as_png')
def save_as_png(backend, f):
    backend.image.save(f, 'PNG')


@PillowBackend.register_operation('save_as_gif')
def save_as_gif(backend, f):
    # All gif files use either the L or P mode but we sometimes convert them
    # to RGB/RGBA to improve the quality of resizing. We must make sure that
    # they are converted back before saving.
    if backend.image.mode not in ['L', 'P']:
        backend.image = backend.image.convert('P', palette=backend.get_pillow_image().ADAPTIVE)

    if 'transparency' in backend.image.info:
        backend.image.save(f, 'GIF', transparency=backend.image.info['transparency'])
    else:
        backend.image.save(f, 'GIF')


@PillowBackend.register_operation('has_alpha')
def has_alpha(backend):
    img = backend.image
    return img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)


@PillowBackend.register_operation('has_animation')
def has_animation(backend):
    # Animation not supported by PIL
    return False


@PillowBackend.register_operation('get_pillow_image')
def get_pillow_image(backend):
    return backend.image.copy()


@PillowBackend.register_operation('auto_orient')
def auto_orient(backend):
        if backend.image.orientation not in ['top_left', 'undefined']:
            if hasattr(backend.image, 'auto_orient'):
                backend.image.auto_orient()
            else:
                orientation_ops = {
                    'top_right': [backend.image.flop],
                    'bottom_right': [functools.partial(backend.image.rotate, degree=180.0)],
                    'bottom_left': [backend.image.flip],
                    'left_top': [backend.image.flip, functools.partial(backend.image.rotate, degree=90.0)],
                    'right_top': [functools.partial(backend.image.rotate, degree=90.0)],
                    'right_bottom': [backend.image.flop, functools.partial(backend.image.rotate, degree=90.0)],
                    'left_bottom': [functools.partial(backend.image.rotate, degree=270.0)]
                }
                fns = orientation_ops.get(backend.image.orientation)

                if fns:
                    for fn in fns:
                        fn()
                    backend.image.orientation = 'top_left'
