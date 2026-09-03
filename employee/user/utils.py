from datetime import date
import calendar

def calculate_exact_age(dob, calculate_on):
    """
    Calculate exact age in years, months and days.
    """

    if calculate_on < dob:
        raise ValueError(
            "Calculation date cannot be before date of birth."
        )

    years = calculate_on.year - dob.year
    months = calculate_on.month - dob.month
    days = calculate_on.day - dob.day

    # Borrow days from previous month
    if days < 0:
        months -= 1

        if calculate_on.month == 1:
            previous_month = 12
            previous_year = calculate_on.year - 1
        else:
            previous_month = calculate_on.month - 1
            previous_year = calculate_on.year

        days_in_previous_month = calendar.monthrange(
            previous_year,
            previous_month
        )[1]

        days += days_in_previous_month

    # Borrow months from previous year
    if months < 0:
        years -= 1
        months += 12

    return years, months, days

def get_zodiac_sign(day, month):

    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Aquarius"

    elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
        return "Pisces"

    elif (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Aries"

    elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Taurus"

    elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Gemini"

    elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Cancer"

    elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Leo"

    elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Virgo"

    elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Libra"

    elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Scorpio"

    elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Sagittarius"

    else:
        return "Capricorn"


def get_generation(birth_year):

    if birth_year <= 1964:
        return "Baby Boomer"

    elif birth_year <= 1980:
        return "Generation X"

    elif birth_year <= 1996:
        return "Millennial"

    elif birth_year <= 2012:
        return "Generation Z"

    else:
        return "Generation Alpha"


def get_next_birthday(dob, calculate_on):
    """
    Calculate the next birthday after calculate_on.

    For February 29 birthdays, February 28 is used
    in non-leap years.
    """

    # Try birthday in the calculation year
    try:
        birthday = date(
            calculate_on.year,
            dob.month,
            dob.day
        )
    except ValueError:
        # February 29 in a non-leap year
        birthday = date(
            calculate_on.year,
            2,
            28
        )

    # If birthday is today or already passed,
    # move to next year.
    if birthday <= calculate_on:

        try:
            birthday = date(
                calculate_on.year + 1,
                dob.month,
                dob.day
            )
        except ValueError:
            # February 29 in a non-leap year
            birthday = date(
                calculate_on.year + 1,
                2,
                28
            )

    days_until_birthday = (
        birthday - calculate_on
    ).days

    return birthday, days_until_birthday



def calculate_age_details(dob, calculate_on):
    """
    Calculate complete age details between DOB
    and the selected calculation date.
    """

    if dob > calculate_on:
        raise ValueError(
            "Date of birth cannot be after calculation date."
        )

    # Exact age
    years, months, days = calculate_exact_age(
        dob,
        calculate_on
    )

    # Total days
    total_days = (
        calculate_on - dob
    ).days

    # Total weeks
    total_weeks = total_days // 7

    # Remaining days after complete weeks
    remaining_days = total_days % 7

    # Total completed calendar months
    total_months = (
        years * 12
    ) + months

    # Total hours
    total_hours = total_days * 24

    # Total minutes
    total_minutes = total_hours * 60

    # Total seconds
    total_seconds = total_minutes * 60

    # Day of birth
    day_of_week_born = dob.strftime("%A")

    # Zodiac
    zodiac_sign = get_zodiac_sign(
        dob.day,
        dob.month
    )

    # Generation
    generation = get_generation(
        dob.year
    )

    # Next birthday
    next_birthday, days_until_birthday = (
        get_next_birthday(
            dob,
            calculate_on
        )
    )

    return {
        "date_of_birth": str(dob),
        "calculation_date": str(calculate_on),

        # Exact age
        "age_years": years,
        "age_months": months,
        "age_days": days,
        "exact_age": (
            f"{years} years, "
            f"{months} months, "
            f"{days} days"
        ),

        # Total time
        "total_months": total_months,
        "total_weeks": total_weeks,
        "total_days": total_days,
        "remaining_days_after_weeks": remaining_days,
        "total_hours": total_hours,
        "total_minutes": total_minutes,
        "total_seconds": total_seconds,

        # Birth information
        "day_of_week_born": day_of_week_born,
        "zodiac_sign": zodiac_sign,
        "generation": generation,

        # Birthday information
        "next_birthday_date": str(next_birthday),
        "next_birthday_in_days": days_until_birthday,
    }
