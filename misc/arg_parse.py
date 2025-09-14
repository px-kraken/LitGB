import re
from typing import Dict, Union


def auto_cast(str_arg: str):
    """
    Attempts to cast a string to an int or float. If neither is possible, returns the original string.

    Args:
        str_arg (str): The input string to cast.

    Returns:
        Union[int, float, str]: The casted value as int, float, or the original string.

    Examples:
        >>> auto_cast("42")
        42

        >>> auto_cast("3.14")
        3.14

        >>> auto_cast("not_a_number")
        'not_a_number'
    """
    try:
        return int(str_arg)
    except ValueError:
        pass

    try:
        return float(str_arg)
    except ValueError:
        pass

    return str_arg


def argdict(argstr: str) -> Dict[str, Union[str, float, int]]:
    """
    Parses a string of key-value pairs into a dictionary, with values automatically cast to int, float, or str.

    Args:
        argstr (str): The input string containing key-value pairs separated by '='.

    Returns:
        Dict[str, Union[str, float, int]]: A dictionary with keys as strings and values as int, float, or str.

    Examples:
        >>> argdict('length = 4 width= 5.5 type = "abc"')
        {'length': 4, 'width': 5.5, 'type': '"abc"'}

        >>> argdict('single=42')
        {'single': 42}
    """
    
    remainder = re.sub(r' *= *', '=', argstr)
    items = remainder.count('=')
    result_argdict = dict()
    while items > 0:

        key, remainder = remainder.split("=", 1)  # type: str, str
        if items > 1:
            value = remainder.split("=", 1)[0][::-1].split(" ", 1)[1][::-1]
            remainder = remainder.replace(value, "", 1)
        else:
            value = remainder
        result_argdict[key.strip()] = auto_cast(value.strip())
        items -= 1

    return result_argdict
