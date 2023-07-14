import os
from datetime import date, timedelta
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable


PROGRAM_LANGUAGES = ['JavaScript', 'Java', 'Python', 'Ruby', 'PHP', 'C++', 'C#', 'Swift', 'Go']
TABLE_HEADING = ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']
LOCATION_FOR_HH = '1'
LOCATION_FOR_SJ = 4
VACANCY_PER_PAGE = 100
START_PAGE = 0
VACANCY_DATE_FROM = date.today() - timedelta(days=30)


def predict_rub_salary_hh(hh_vacancy):
    salary = hh_vacancy['salary']
    if not salary or salary['currency'] != 'RUR':
        return None
    else:
        return get_average_value(salary['to'], salary['from'])


def predict_rub_salary_sj(sj_vacancy):
    if sj_vacancy['currency'] != 'rub' or (not sj_vacancy['payment_from'] and not sj_vacancy['payment_to']):
        return None
    else:
        return get_average_value(sj_vacancy['payment_from'], sj_vacancy['payment_to'])


def get_average_value(min_value, max_value):
    if not max_value:
        return min_value * 1.2
    elif not min_value:
        return max_value * 0.8
    else:
        return (min_value + max_value) / 2


def get_vacancies_stats_from_hh():
    hh_url = 'https://api.hh.ru/vacancies'
    hh_vacancies_stats = {}
    for program_language in PROGRAM_LANGUAGES:
        params = {'text': program_language,
                  'area': LOCATION_FOR_HH,
                  'per_page': VACANCY_PER_PAGE,
                  'page': START_PAGE,
                  'date_from': VACANCY_DATE_FROM}
        vacancy_pages_count = None
        vacancy_with_salaries = 0
        vacancy_salaries_sum = 0
        while params['page'] != vacancy_pages_count:
            hh_response = requests.get(hh_url, params=params)
            hh_response.raise_for_status()
            vacancies_on_page = hh_response.json()
            vacancy_pages_count = vacancies_on_page['pages']
            for vacancy in vacancies_on_page['items']:
                vacancy_salary = predict_rub_salary_hh(vacancy)
                if vacancy_salary:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += vacancy_salary
            params['page'] += 1
        average_salary = int(vacancy_salaries_sum / vacancy_with_salaries) if vacancy_with_salaries else 0
        vacancy_attribute = {'vacancies_found': vacancies_on_page['found'],
                             'vacancies_processed': vacancy_with_salaries,
                             'average_salary': average_salary}
        hh_vacancies_stats[program_language] = vacancy_attribute
    return hh_vacancies_stats


def get_vacancies_stats_from_sj(api_key):
    sj_vacancies_stats = {}
    for program_language in PROGRAM_LANGUAGES:
        superjob_url = 'https://api.superjob.ru/2.0/vacancies/'
        superjob_params = {'keyword': program_language,
                           'town': LOCATION_FOR_SJ,
                           'page': START_PAGE,
                           'count': VACANCY_PER_PAGE
                           }
        vacancy_with_salaries = 0
        vacancy_salaries_sum = 0
        while True:
            superjob_response = requests.get(superjob_url, headers=api_key, params=superjob_params)
            superjob_response.raise_for_status()
            vacancies_on_page = superjob_response.json()
            for vacancy in vacancies_on_page['objects']:
                vacancy_salary = predict_rub_salary_sj(vacancy)
                if vacancy_salary:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += vacancy_salary
            if not vacancies_on_page['more']:
                break
            superjob_params['page'] += 1
        average_salary = int(vacancy_salaries_sum / vacancy_with_salaries) if vacancy_with_salaries else 0
        vacancy_attribute = {'vacancies_found': vacancies_on_page['total'],
                             'vacancies_processed': vacancy_with_salaries,
                             'average_salary': average_salary}
        sj_vacancies_stats[program_language] = vacancy_attribute
    return sj_vacancies_stats


def create_table(vacancies, table_name):
    table = [
        TABLE_HEADING,
    ]
    for program_language in vacancies:
        table_row = [program_language, vacancies[program_language]['vacancies_found'],
                     vacancies[program_language]['vacancies_processed'],
                     vacancies[program_language]['average_salary']]
        table.append(table_row)
    return AsciiTable(table, table_name)


if __name__ == '__main__':
    load_dotenv()
    superjob_auth = {'X-Api-App-Id': f'{os.getenv("SUPERJOB_TOKEN")}'}
    hh_vacancies = get_vacancies_stats_from_hh()
    sj_vacancies = get_vacancies_stats_from_sj(superjob_auth)
    hh_vacancies_table = create_table(hh_vacancies, 'HH Moscow')
    sj_vacancies_table = create_table(sj_vacancies, 'SuperJob Moscow')
    print(hh_vacancies_table.table)
    print(sj_vacancies_table.table)
