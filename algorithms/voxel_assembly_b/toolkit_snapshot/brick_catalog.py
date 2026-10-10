"""Standard rectangular unit-height bricks; no mesh data bundled."""
BRICKGPT_PARTS = {(1,1): '3005.dat', (1,2): '3004.dat', (1,4): '3010.dat',
                 (1,6): '3009.dat', (1,8): '3008.dat', (2,2): '3003.dat',
                 (2,4): '3001.dat', (2,6): '2456.dat'}
EXTENDED_PARTS = {**BRICKGPT_PARTS, (1,3): '3622.dat', (2,3): '3002.dat', (2,8): '3007.dat'}
# Preserve original public ordering for old callers and token grammar tests.
BRICKGPT_DIMENSIONS = ((1,1),(1,2),(2,1),(1,4),(4,1),(1,6),(6,1),
                      (1,8),(8,1),(2,2),(2,4),(4,2),(2,6),(6,2))
EXTENDED_DIMENSIONS = BRICKGPT_DIMENSIONS + ((1,3),(3,1),(2,3),(3,2),(2,8),(8,2))


def dimensions_for_library(name):
    if name == 'brickgpt':
        return BRICKGPT_DIMENSIONS
    if name == 'extended':
        return EXTENDED_DIMENSIONS
    raise ValueError('brick_library must be brickgpt or extended')
