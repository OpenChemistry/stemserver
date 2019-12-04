from stempy import image
from stempy.pipeline import pipeline, parameter, PipelineIO, PipelineAggregation
import h5py
from mpi4py import MPI

@pipeline('Maximum Diffraction', 'Get the maximum diffraction for a given group of frams', PipelineIO.FRAME, PipelineIO.FRAME, PipelineAggregation.MAX)
@parameter('x', type='integer', label='Origin X', default=-1)
@parameter('y', type='integer', label='Origin Y', default=-1)
@parameter('width', type='integer', label='Width', default=0)
@parameter('height', type='integer', label='Height', default=0)
@parameter('version', type='integer', label='File version', default=3)
def execute(reader, **params):
    origin_x = params.get('x')
    origin_y = params.get('y')
    selection_width = params.get('width')
    selection_height = params.get('height')

    if (isinstance(reader, h5py.File)):
        raise Exception("This pipeline is currently only implemented for raw datasets.")
    else:
        local_stem = image.maximum_diffraction_pattern(reader)

    return local_stem
