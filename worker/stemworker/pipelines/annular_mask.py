from stempy import image
from stempy.pipeline import pipeline, parameter

@pipeline('Annular Mask', 'Creates STEM images using annular masks')
@parameter('centerX', type='integer', label='Center X', default=-1)
@parameter('centerY', type='integer', label='Center Y', default=-1)
@parameter('innerRadius', type='integer', label='Inner Radius', default=0)
@parameter('outerRadius', type='integer', label='Outer Radius', default=0)
@parameter('version', type='integer', label='File version', default=3)
def execute(reader, **params):
    center_x = params.get('centerX')
    center_y = params.get('centerY')
    inner_radius = params.get('innerRadius')
    outer_radius = params.get('outerRadius')

    local_stem = image.create_stem_image(reader, int(inner_radius), int(outer_radius),
                                         center_x=int(center_x), center_y=int(center_y))

    return local_stem
