import csv
import datetime as dt
import os
from dataclasses import InitVar, dataclass
from typing import Any, BinaryIO, Callable, Literal, TextIO, overload

from fpdf import FPDF

SCHOLAR_YEAR = 2023  # année de la rentrée
# COLLOSCOPE_PATH = "./data/colloscope.csv"  # path to the colloscope csv file
COLLOSCOPE_PATH = "/Users/pierre/Documents/dev/projects/hosted/maintained/another-mp2i-bot/resources/colloscope.csv"


def get_date(week: str, week_day: str) -> dt.date:
    week_days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"]

    # dates are formatted like this: "dd/mm-dd/mm"
    # we only care about the first day of the week
    day, month = map(int, week.split("-")[0].split("/"))

    if int(month) > 8:
        year = SCHOLAR_YEAR
    else:
        year = SCHOLAR_YEAR + 1

    date = dt.date(year, month, day)
    delta = dt.timedelta(days=week_days.index(week_day))

    return date + delta


@dataclass
class ColleData:
    group: str
    subject: str
    professor: str
    week: InitVar[str]  # format: "dd/mm-dd/mm"
    week_day: str
    hour: str
    classroom: str

    def __post_init__(self, week: str):
        self.week_day = self.week_day.lower()
        self.date: dt.date = get_date(week, self.week_day)

    def __str__(self):
        return (
            f"Le {self.str_date}, passe le groupe {self.group} en {self.classroom} avec {self.professor} à {self.hour}"
        )

    @property
    def str_date(self) -> str:
        return self.date.strftime("%d/%m/%Y")

    @property
    def long_str_date(self) -> str:
        """
        Return the date in a human readable format :
        Ex: "Lundi 10 janvier"
        """
        monthName = [
            "janvier",
            "février",
            "mars",
            "avril",
            "mai",
            "juin",
            "juillet",
            "août",
            "septembre",
            "octobre",
            "novembre",
            "décembre",
        ]

        return f"{self.week_day} {self.date.day} {monthName[self.date.month - 1]}"


def sort_colles(
    colles_datas: list[ColleData], sort_type: Literal["temps", "prof", "groupe"] = "temps"
) -> list[ColleData]:
    key: Callable[[ColleData], Any]
    match sort_type:
        case "temps":
            key = lambda c: c.date
        case "prof":
            key = lambda c: c.professor
        case "groupe":
            key = lambda c: c.group
    return sorted(colles_datas, key=key)


def get_all_colles(filename: str) -> list[ColleData]:
    """
    Returns a list of all the collesDatas by reading the csv file
    """
    colles: list[ColleData] = []

    with open(filename, encoding="utf-8", errors="ignore") as f:
        csv_reader = csv.reader(f, delimiter=",")

        header = next(csv_reader)
        for row in csv_reader:
            subject, professor, day, hour, classroom = row[0:5]
            for x in range(5, len(row)):  # iterate over each colles columns
                group = row[x]
                week = header[x]
                if group != "":
                    colles.append(ColleData(group, subject, professor, week, day, hour, classroom))

    return colles


def get_holidays(filename: str) -> list[dt.date]:
    """Return the holydays dates"""
    with open(filename, encoding="utf-8", errors="ignore") as f:
        csv_reader = csv.reader(f, delimiter=",")

        holidays: list[dt.date] = []
        header = next(csv_reader)

    for i, week in enumerate(header):
        if week.lower() == "vacances":
            if not header[i - 1]:
                continue
            week = get_date(header[i - 1], "lundi")
            holidays.append(week + dt.timedelta(days=7))  # add vacances to list

    return holidays


def convert_hour(raw_time: str) -> str:
    """Change the hour format from "xh" to "x:xx AM/PM"
    Ex: 10h00 -> 10:00 AM
        18h00 -> 6:00 PM

    Args:
        heure (string): Ex: 18h00
    """
    time = raw_time.split("h")
    minutes = "00" if time[1] == "" else time[1]
    hours = int(time[0])
    if hours >= 12:
        return f"{hours - 12}:{minutes} PM"
    else:
        return f"{hours}:{minutes} AM"


def add_one_hour(time: str) -> str:
    """Ajoute une heure à l'heure donnée (pas de colle a minuit donc flemme)

    Args:
        time (string): Ex: 10:00 AM
    """

    hour, rest = time.split(":")
    hour = int(hour)
    if hour == 12:
        return f"1:{rest.split(' ')[0]} PM"
    else:
        return f"{hour + 1}:{rest}"


@overload
def write_colles(
    file: TextIO,
    export_type: Literal["csv", "agenda", "todoist"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
) -> None:
    ...


@overload
def write_colles(
    file: BinaryIO,
    export_type: Literal["pdf"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
) -> None:
    ...


def write_colles(
    file: TextIO | BinaryIO,
    export_type: Literal["pdf", "csv", "agenda", "todoist"],
    colles_datas: list[ColleData],
    group: str,
    holidays: list[dt.date],
):
    export_path = f"./groupe{group}"

    if os.path.exists(export_path) == False:
        os.mkdir(export_path)

    def csv_method(f: TextIO):
        # write the sorted data into a csv file
        writer = csv.writer(f, delimiter=",")
        writer.writerow(["date", "heure", "prof", "salle", "matière"])

        for colle in colles_datas:
            data = [colle.str_date, colle.hour, colle.professor, colle.classroom, colle.subject]
            writer.writerow(data)

    def agenda_method(f: TextIO):
        agenda: list[dict[str, Any]] = []
        for colle in colles_datas:
            agenda.append(
                {
                    "Subject": f"{colle.subject} {colle.professor} {colle.classroom}",
                    "Start Date": colle.str_date,
                    "Start Time": convert_hour(colle.hour),
                    "End Date": colle.str_date,
                    "End Time": add_one_hour(convert_hour(colle.hour)),
                    "All Day Event": False,
                    "Description": f"Colle de {colle.subject} avec {colle.professor} en {colle.classroom} a {colle.hour}",
                    "Location": colle.classroom,
                }
            )

        fieldnames = [
            "Subject",
            "Start Date",
            "Start Time",
            "End Date",
            "End Time",
            "All Day Event",
            "Description",
            "Location",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for colle in agenda:
            writer.writerow(colle)

    def todoist_method(f: TextIO):
        type, priority = "task", 2
        todoist: list[dict[str, Any]] = []
        for colle in colles_datas:
            todoist.append(
                {
                    "TYPE": type,
                    "CONTENT": f"Colle de {colle.subject} avec {colle.professor}",
                    "DESCRIPTION": f"Salle {colle.classroom}",
                    "PRIORITY": priority,
                    "INDENT": "",
                    "AUTHOR": "",
                    "RESPONSIBLE": "",
                    "DATE": colle.str_date + " " + colle.hour,
                    "DATE_LANG": "fr",
                    "TIMEZONE": "Europe/Paris",
                }
            )

        fieldnames = [
            "TYPE",
            "CONTENT",
            "DESCRIPTION",
            "PRIORITY",
            "INDENT",
            "AUTHOR",
            "RESPONSIBLE",
            "DATE",
            "DATE_LANG",
            "TIMEZONE",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()
        for colle in todoist:
            writer.writerow(colle)

    def pdf_method(f: BinaryIO):
        vacanceIndex = 0
        pdf = FPDF()
        pdf.add_font("Arial", "", "./resources/fonts/arial.ttf")
        pdf.add_font("Arial", "B", "./resources/fonts/arial_bold.ttf")
        pdf.add_page()
        page_width = pdf.w - 2 * pdf.l_margin

        pdf.set_font("Arial", "U", 14)
        pdf.cell(page_width, 0.0, f"Colloscope groupe {group}", align="C")
        pdf.ln(10)

        pdf.set_font("Arial", "", 11)

        col_width = page_width / 4

        pdf.ln(1)

        th = pdf.font_size + 2

        pdf.set_font("Arial", "B", 11)
        pdf.cell(10, th, text="Id", border=1, align="C")  # type: ignore
        pdf.cell(40, th, "Date", border=1, align="C")
        pdf.cell(20, th, "Heure", border=1, align="C")
        pdf.cell(col_width * 0.75, th, "Prof", border=1, align="C")
        pdf.cell(30, th, "Salle", border=1, align="C")
        pdf.cell(col_width, th, "Matiere", border=1, align="C")
        pdf.set_font("Arial", "", 11)
        pdf.ln(th)

        for i, colle in enumerate(colles_datas, 1):
            if vacanceIndex < len(holidays):  # fait un saut de ligne à chaque vacances
                if colle.date > holidays[vacanceIndex]:
                    pdf.ln(th * 0.5)
                    pdf.set_font("Arial", "B", 14)
                    pdf.cell(90 + 2 * col_width, th, f"Vacances", align="C")
                    pdf.set_font("Arial", "", 11)
                    pdf.ln(th * 1.5)
                    vacanceIndex += 1
            pdf.cell(10, th, str(i), border=1, align="C")
            pdf.set_font("Arial", "", 9)
            pdf.cell(40, th, colle.long_str_date, border=1, align="C")
            pdf.set_font("Arial", "", 11)
            pdf.cell(20, th, colle.hour, border=1, align="C")
            pdf.cell(col_width * 0.75, th, colle.professor, border=1, align="C")
            pdf.cell(30, th, colle.classroom, border=1, align="C")
            pdf.cell(col_width, th, colle.subject, border=1, align="C")
            pdf.ln(th)

        pdf.ln(10)

        pdf.set_font("Times", "", 10)
        pdf.output(f)  # type: ignore

    match export_type:
        case "csv":
            assert isinstance(file, TextIO)
            return csv_method(file)
        case "agenda":
            assert isinstance(file, TextIO)
            return agenda_method(file)
        case "pdf":
            assert isinstance(file, BinaryIO)
            return pdf_method(file)
        case "todoist":
            assert isinstance(file, TextIO)
            return todoist_method(file)


def get_group_upcoming_colles(colles: list[ColleData], group: str) -> list[ColleData]:
    colles = sort_colles(colles, sort_type="temps")  # sort by time
    today = dt.datetime.now() + dt.timedelta(days=-1)  # date de la veille

    filtered_colles = [c for c in colles if c.group == group and c.date < today]
    return filtered_colles


# def main(group: str, export_type: Literal["pdf", "csv", "agenda", "todoist"] = "pdf"):
#     colles = get_all_colles(COLLOSCOPE_PATH)  # list of ColleData objects
#     holidays = get_holidays(COLLOSCOPE_PATH)
#     colles = sort_colles(colles, sort_type="temps")  # sort by time

#     filtered_colles = [c for c in colles if c.group == group]
#     if not filtered_colles:
#         raise ValueError("Aucune colle n'a été trouvé pour ce groupe")

#     with open("test.pdf", "wb") as f:
#         write_colles(f, "pdf", filtered_colles, group, holidays)
