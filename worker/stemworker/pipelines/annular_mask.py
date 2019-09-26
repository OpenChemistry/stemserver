from stempy import image
from stempy.pipeline import pipeline, parameter
import h5py

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

    if (isinstance(reader, h5py.File)):
        frames_path = '/electron_events/frames'
        scans_path = '/electron_events/scan_positions'
        data = reader[frames_path][()]
        frame_width = reader[frames_path].attrs['Nx']
        frame_height = reader[frames_path].attrs['Ny']
        width = reader[scans_path].attrs['Nx']
        height = reader[scans_path].attrs['Ny']
        local_stem = image.create_stem_image_sparse(data, int(inner_radius), int(outer_radius),
                                                    frame_width=frame_width, frame_height=frame_height,
                                                    width=width, height=height,
                                                    center_x=int(center_x), center_y=int(center_y))
    else:
        local_stem = image.create_stem_image(reader, int(inner_radius), int(outer_radius),
                                             center_x=int(center_x), center_y=int(center_y))

    return local_stem
