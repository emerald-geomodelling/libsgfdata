import click
import importlib.metadata

parsers = {entry.name: entry for entry in importlib.metadata.entry_points()['libsgfdata.parsers']}
dumpers = {entry.name: entry for entry in importlib.metadata.entry_points()['libsgfdata.dumpers']}
transforms = {entry.name: entry for entry in importlib.metadata.entry_points()['libsgfdata.transforms']}

def add_transforms(fn):
    for entry in transforms.values():
        fn = entry.load().decorate(fn)
    return fn

@click.command()
@add_transforms
@click.option('--informat', default="sgf", help='Input format: %s' % ", ".join(parsers.keys()))
@click.option('--outformat', default="sgf", help='Ouput format: %s' % ", ".join(dumpers.keys()))
@click.argument('input', type=click.File('rb'))
@click.argument('output', type=click.File('wb'))
def main(informat, outformat, input, output, **kw):
    """Convert between borehole file formats"""

    assert informat in parsers, "Unknown input format: %s" % informat
    assert outformat in dumpers, "Unknown output format: %s" % outformat
    
    data = parsers[informat].load()(input)

    for name, value in kw.items():
        if name in transforms and value:
            data = transforms[name].load().transform(data, **kw)
    
    dumpers[outformat].load()(data, output)
    
if __name__ == '__main__':
    main()
