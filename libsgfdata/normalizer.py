import logging
from . import metadata

logger = logging.getLogger(__name__)

def normalize(sections):
    for section in sections:
        for blockname, block in section.items():
            normalization = metadata.block_metadata[blockname].loc[
                ~metadata.block_metadata[blockname].normalization.isna()
            ].set_index("ident").normalization
            normalization = metadata.block_metadata[blockname].loc[normalization].set_index(normalization.index).ident
            if isinstance(block, list):
                for row in block:
                    for orig, repl in normalization.items():
                        if orig in row:
                            row[repl] = row.pop(orig)
            else:
                block.rename(columns=normalization.to_dict(), inplace=True)
