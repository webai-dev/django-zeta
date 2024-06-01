def list_to_dict(source):
    """
    Change list to dictionary, with list elements as values and positions as keys.

    Args:
        - source (List)

    Returns:
        Dict
    """
    output = {}
    counter = 1  # Start keys here
    for item in source:
        output[counter] = item
        counter += 1
    return output


def num_check(num):
    """
    Confirms given number str is an integer.

    Args:
        - num (str)

    Raises:
        ValueError: If num is not an integer.

    Returns:
        int: Integer casted initial num.
    """
    while not isinstance(num, int):
        try:
            val = int(num)
            return val
        except ValueError:
            num = input("Please enter an integer number: ")


def dict_check(num, choices):
    """
    Confirms user given entry is a key in dictionary created by list_to_dict.

    Args:
        - num (str)
        - choices (Dict)

    Returns:
        str: User given entry.
    """
    while True:
        num = num_check(num)
        if num in choices:
            return num
        num = input('Please enter a number from the list: ')


def dict_display(choices):
    """
    Display keys, values in dictionary.

    Args:
        - choices (Dict)
    """
    for key, value in choices.items():
        print(key, value)


def choose(message, choices):
    """
    Choose a list element (str) and return position in list.

    Args:
        - message (str): Help message.
        - choices (List)

    Returns:
        Optional[int]: Choice picked by user.
    """
    print(message)
    dic = list_to_dict(choices)
    dict_display(dic)
    print()
    # get choice
    choice_loc = dict_check(input('Enter choice here: '), dic)
    if choice_loc is not None:
        loc = int(choice_loc) - 1  # list and dictionary have - 1 index diff
        return loc
    return None


def confirm(item):
    """
    Confirms user entry.

    Args:
        - item (str): Initial user entry.

    Returns:
        item (str): Either initial or new value given by user.
    """
    while True:
        ##Messages
        choice = choose('Are you sure you want to enter ' + item + '?', ["No", "Yes"])
        if choice == 0:
            item = input('Please enter the correct item: ')
        elif choice == 1:
            return item
