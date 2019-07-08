import glob
from stempy import io, image
import numpy as np
from mpi4py import MPI


from stempy.pipeline import pipeline, parameter

@pipeline('Annular Mask', 'Creates STEM images using annular masks')
@parameter('centerX', type='integer', label='Center X', default=-1)
@parameter('centerY', type='integer', label='Center Y', default=-1)
@parameter('innerRadius', type='integer', label='Inner Radius', default=0)
@parameter('outerRadius', type='integer', label='Outer Radius', default=0)
@parameter('version', type='integer', label='File version', default=3)
def execute(path=None, **params):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    world_size = comm.Get_size()

    center_x = params.get('centerX')
    center_y = params.get('centerY')
    inner_radius = params.get('innerRadius')
    outer_radius = params.get('outerRadius')

    # TODO: In future this should be done by the infrastructure.
    files = glob.glob(path)
    files_per_rank = len(files) // world_size
    left_over = len(files) % world_size
    if rank < left_over:
        offset = rank*(files_per_rank+1)
        files = files[offset:offset+files_per_rank+1]
    else:
        offset = rank*files_per_rank+left_over
        files = files[offset:offset+files_per_rank]

    # Create local stem
    reader = io.reader(files, version=int(params.get('version')))

    local_stem = image.create_stem_image(reader, int(inner_radius), int(outer_radius),
                                         center_x=int(center_x), center_y=int(center_y))

    return local_stem
