import logging

solver_dict = {
    "1Inch": [0, 0],
    "Raven": [0, 0],
    "0x": [0, 0],
    "PLM": [0, 0],
    "Quasilabs": [0, 0],
    "Otex": [0, 0],
    "SeaSolver": [0, 0],
    "Laertes": [0, 0],
    "ParaSwap": [0, 0],
    "BalancerSOR": [0, 0],
    "BaselineSolver": [0, 0],
    "Legacy": [0, 0],
    "NaiveSolver": [0, 0],
    "DMA": [0, 0],
    "CowDexAg": [0, 0],
    "Barter": [0, 0],
}
header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}


def get_logger(filename):
    logger = logging.getLogger(filename)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(filename + ".log", mode="w")
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger
