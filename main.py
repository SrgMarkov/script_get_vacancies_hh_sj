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
    if not salary:
        return None
    elif salary['currency'] != 'RUR':
        return None
    elif not salary['from']:
        return salary['to'] * 0.8
    elif not salary['to']:
        return salary['from'] * 1.2
    else:
        return (salary['to'] + salary['from']) / 2


def predict_rub_salary_sj(sj_vacancy):
    if sj_vacancy['currency'] != 'rub' or (sj_vacancy['payment_from'] == 0 and sj_vacancy['payment_to'] == 0):
        return None
    elif sj_vacancy['payment_from'] == 0:
        return sj_vacancy['payment_to'] * 0.8
    elif sj_vacancy['payment_to'] == 0:
        return sj_vacancy['payment_from'] * 1.2
    else:
        return (sj_vacancy['payment_from'] + sj_vacancy['payment_to']) / 2


def get_vacancies_stats_from_hh():
    hh_url = 'https://api.hh.ru/vacancies'
    hh_vacancies_stats = {}
    for program_language in PROGRAM_LANGUAGES:
        params = {'text': program_language,
                  'area': LOCATION_FOR_HH,
                  'per_page': VACANCY_PER_PAGE,
                  'page': START_PAGE,
                  'date_from': VACANCY_DATE_FROM}
        vacancy_pages = None
        vacancy_attribute = None
        vacancy_with_salaries = 0
        vacancy_salaries_sum = 0
        while params['page'] != vacancy_pages:
            vacancy = requests.get(hh_url, params=params)
            vacancy.raise_for_status()
            vacancy_response = vacancy.json()
            vacancy_pages = vacancy_response['pages']
            for vacancy in vacancy_response['items']:
                vacancy_salary = predict_rub_salary_hh(vacancy)
                if vacancy_salary:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += vacancy_salary
            vacancy_attribute = {'vacancies_found': vacancy_response['found'],
                                 'vacancies_processed': vacancy_with_salaries,
                                 'average_salary': int(vacancy_salaries_sum / vacancy_with_salaries)}
            params['page'] += 1
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
            vacancies_on_page_json = superjob_response.json()
            for vacancy in vacancies_on_page_json['objects']:
                vacancy_salary = predict_rub_salary_sj(vacancy)
                if vacancy_salary:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += vacancy_salary
            vacancy_attribute = {'vacancies_found': superjob_response.json()['total'],
                                 'vacancies_processed': vacancy_with_salaries,
                                 'average_salary': int(vacancy_salaries_sum / vacancy_with_salaries)}
            if not vacancies_on_page_json['more']:
                break
            superjob_params['page'] += 1
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
    hh_vacancies_table = create_table(get_vacancies_stats_from_hh(), 'HH Moscow')
    sj_vacancies_table = create_table(get_vacancies_stats_from_sj(superjob_auth), 'SuperJob Moscow')
    print(hh_vacancies_table.table)
    print(sj_vacancies_table.table)
