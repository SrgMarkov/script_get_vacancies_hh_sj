import os
from datetime import date, timedelta
import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable

PROGRAM_LANGUAGES = ['JavaScript', 'Java', 'Python', 'Ruby', 'PHP', 'C++', 'C#', 'Swift', 'Go']
TABLE_HEADING = ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']


def predict_rub_salary_hh(hh_vacancy):
    salary = hh_vacancy['salary']
    if salary is None:
        return None
    elif salary['currency'] != 'RUR':
        return None
    elif salary['from'] is None:
        return salary['to'] * 0.8
    elif salary['to'] is None:
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


def get_vacancies_from_hh():
    hh_url = 'https://api.hh.ru/vacancies'
    hh_vacancies = {}
    for program_language in PROGRAM_LANGUAGES:
        params = {'text': program_language,
                  'area': '1',
                  'per_page': 100,
                  'page': 0,
                  'date_from': date.today() - timedelta(days=30)}
        vacancy_pages = None
        vacancy_with_salaries = 0
        vacancy_salaries_sum = 0
        vacancy_attribute = {}
        while params['page'] != vacancy_pages:
            vacancy = requests.get(hh_url, params=params)
            vacancy.raise_for_status()
            vacancy_pages = vacancy.json()['pages']
            vacancy_attribute['vacancies_found'] = vacancy.json()['found']
            for vacancy in vacancy.json()['items']:
                if predict_rub_salary_hh(vacancy) is not None:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += predict_rub_salary_hh(vacancy)
            params['page'] += 1
        vacancy_attribute['vacancies_processed'] = vacancy_with_salaries
        vacancy_attribute['average_salary'] = int(vacancy_salaries_sum / vacancy_with_salaries)
        hh_vacancies[program_language] = vacancy_attribute
    return hh_vacancies


def get_vacancies_from_sj():
    sj_vacancies = {}
    for program_language in PROGRAM_LANGUAGES:
        superjob_auth = {'X-Api-App-Id': f'{os.getenv("SUPERJOB_TOKEN")}'}
        superjob_url = 'https://api.superjob.ru/2.0/vacancies/'
        superjob_params = {'keyword': program_language,
                           'town': 4,
                           'page': 0,
                           'count': 100
                           }
        vacancy_with_salaries = 0
        vacancy_salaries_sum = 0
        vacancy_attribute = {}
        while True:
            superjob_response = requests.get(superjob_url, headers=superjob_auth, params=superjob_params)
            superjob_response.raise_for_status()
            vacancy_attribute['vacancies_found'] = superjob_response.json()['total']
            for vacancy in superjob_response.json()['objects']:
                if predict_rub_salary_sj(vacancy) is not None:
                    vacancy_with_salaries += 1
                    vacancy_salaries_sum += predict_rub_salary_sj(vacancy)
            vacancy_attribute['vacancies_processed'] = vacancy_with_salaries
            vacancy_attribute['average_salary'] = int(vacancy_salaries_sum / vacancy_with_salaries)
            if not superjob_response.json()['more']:
                break
            superjob_params['page'] += 1
        sj_vacancies[program_language] = vacancy_attribute
    return sj_vacancies


def create_table(vacancies, table_name):
    hh_table_data = [
        TABLE_HEADING,
    ]
    for program_language in vacancies:
        hh_table_row = [program_language, vacancies[program_language]['vacancies_found'],
                        vacancies[program_language]['vacancies_processed'],
                        vacancies[program_language]['average_salary']]
        hh_table_data.append(hh_table_row)
    return AsciiTable(hh_table_data, table_name)


if __name__ == '__main__':
    load_dotenv()
    hh_vacancies_table = create_table(get_vacancies_from_hh(), 'HH Moscow')
    sj_vacancies_table = create_table(get_vacancies_from_sj(), 'SuperJob Moscow')
    print(hh_vacancies_table.table)
    print(sj_vacancies_table.table)
