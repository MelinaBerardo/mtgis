

def parsePreOccupiedNums(usedNums:str):
    def normalize(num_str:str, sep=',', sep_range='-'):
        # Converts a comma and dash sparated string into a list of ints (eg 1-4,6,7,10-12 to [1,2,3,4,6,7,10,11,12])
        for k in num_str.split(sep):
            if sep_range not in k:
                yield int(k)
            else:
                _r1, _r2 = [int(j) for j in k.split(sep_range)]
                yield from range(_r1, _r2 + 1)
    if usedNums and len(usedNums)>0:
        return sorted(normalize(usedNums))
    else:
        return []
    
# see https://stackoverflow.com/questions/24483182/python-split-list-into-n-chunks
def chunks(l, n):
    """Yield n number of sequential chunks from l."""
    d, r = divmod(len(l), n)
    for i in range(n):
        si = (d+1)*(i if i < r else r) + d*(0 if i < r else i - r)
        yield l[si:si+(d+1 if i < r else d)]


def formatNumsAsRanges(nums, prefix=' ', sep=', ', sep_range='-'):
    # convierte una lista de ints en un string con rangos
    #   (ej [1,2,3,4,6,7,10,11,12] to ' 1-4, 6, 7, 10-12')
    blocks = []
    for num in sorted(nums):
        if blocks and num == blocks[-1][1] + 1:
            blocks[-1][1] = num
        elif not blocks or num != blocks[-1][1]:
            blocks.append([num, num])

    parts = []
    for a, b in blocks:
        if a == b:
            parts.append(str(a))
        else:
            parts.append(str(a) + sep_range + str(b))

    return prefix + sep.join(parts)