
from datetime import date, timedelta

def get_summer_dates(year):
    '''
    Calculate the start and end dates for the Summer term of a given year.

    Rules:
    - Starts: Last Monday in June
    - Ends: First Friday of September (typically the first full week)

    Parameters:
    year (int): The year for which the Summer term dates are to be calculated.

    Returns:
    tuple: (start_date, end_date) as datetime.date objects
    '''
    d = date(year, 6, 30)
    while d.weekday() != 0:  # Find last Monday in June
        d -= timedelta(days=1)
    start_date = d

    d = date(year, 9, 1)
    while d.weekday() != 4:  # Find first Friday in September
        d += timedelta(days=1)
    end_date = d

    return start_date, end_date

def get_fall_dates(year):
    '''
    Calculate the start and end dates for the Fall term of a given year.

    Rules:
    - Starts: Last Monday of September
    - Ends: Second Friday in December (finals end)

    Parameters:
    year (int): The year for which the Fall term dates are to be calculated.

    Returns:
    tuple: (start_date, end_date) as datetime.date objects
    '''
    d = date(year, 9, 30)
    while d.weekday() != 0:
        d -= timedelta(days=1)
    start_date = d

    # First Friday of December
    end_teaching = date(year, 12, 1)
    while end_teaching.weekday() != 4:
        end_teaching += timedelta(days=1)

    final_exam_end = end_teaching + timedelta(days=7)  # Finals end following Friday
    return start_date, final_exam_end

def get_winter_dates(year):
    '''
    Calculate the start and end dates for the Winter term of a given year.

    Rules:
    - Starts: First Monday on or after January 1
    - Ends: 11 weeks later on a Friday (10 weeks of class + 1 week finals)

    Parameters:
    year (int): The year for which the Winter term dates are to be calculated.

    Returns:
    tuple: (start_date, end_date) as datetime.date objects
    '''
    d = date(year, 1, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    start_date = d

    end_date = start_date + timedelta(weeks=11) - timedelta(days=1)
    return start_date, end_date

def get_spring_dates(year):
    '''
    Calculate the start and end dates for the Spring term of a given year.

    Rules:
    - Starts: Last Monday in March OR First Monday in April
    - Ends: 11 weeks later on a Friday (10 weeks of class + 1 week finals)

    Parameters:
    year (int): The year for which the Spring term dates are to be calculated.

    Returns:
    tuple: (start_date, end_date) as datetime.date objects
    '''
    d = date(year, 3, 31)
    if d.weekday() != 0:
        while d.weekday() != 0:
            d -= timedelta(days=1)
        if d.day < 25:  # too early, roll to April
            d = date(year, 4, 1)
            while d.weekday() != 0:
                d += timedelta(days=1)
    start_date = d

    end_date = start_date + timedelta(weeks=11) - timedelta(days=1)
    return start_date, end_date

def get_term_dates(term, year):
    '''
    Master function to get the start and end dates of any academic term.

    Parameters:
    term (str): One of "spring", "summer", "fall", or "winter"
    year (int): The academic year

    Returns:
    tuple: (start_date, end_date) as datetime.date objects
    '''
    term = term.lower()
    if term == "summer":
        return get_summer_dates(year)
    elif term == "fall":
        return get_fall_dates(year)
    elif term == "winter":
        return get_winter_dates(year)
    elif term == "spring":
        return get_spring_dates(year)
    else:
        raise ValueError("Invalid term name. Use 'spring', 'summer', 'fall', or 'winter'.")

if __name__ == "__main__":
    # Demonstration: Print term dates for all terms in a sample year
    sample_year = 2026
    for term in ["spring", "summer", "fall", "winter"]:
        start, end = get_term_dates(term, sample_year)
        print(f"{term.capitalize()} {sample_year}: Start = {start}, End = {end}")
