import glob
from stempy import io, image
import numpy as np
from mpi4py import MPI


from stempy.pipeline import pipeline

width = 160
height = 160


@pipeline('Annular Mask', 'Creates STEM images using annular masks')
def execute(path=None, centerX=None, centerY=None, minRadius=None, maxRadius=None):
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    world_size = comm.Get_size()

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
    reader = io.reader(files, version=io.FileVersion.VERSION1)

    local_stem = image.create_stem_image(reader, int(minRadius), int(maxRadius), width, height,
                                         int(centerX), int(centerY))

    return local_stem
