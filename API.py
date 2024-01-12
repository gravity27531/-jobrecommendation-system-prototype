from flask import Flask
from flask_restful import Resource, Api
import requests
from bs4 import BeautifulSoup
import openpyxl
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import re
import schedule
import time

app = Flask(__name__)
api = Api(app)

class JobScraper(Resource):
    def get(self, page):
        position_list, company_list, visitors_list = [], [], []

        while page <= 10:
            url = f'https://www.jobbkk.com/%E0%B8%AB%E0%B8%B2%E0%B8%87%E0%B8%B2%E0%B8%99/%E0%B8%81%E0%B8%A3%E0%B8%B8%E0%B8%87%E0%B9%80%E0%B8%97%E0%B8%9E%E0%B8%A1%E0%B8%AB%E0%B8%B2%E0%B8%99%E0%B8%84%E0%B8%A3/{page}'
            response = requests.get(url)
            html_page = BeautifulSoup(response.content, 'html.parser')
            all_links = html_page.find_all('a', {'class': 'positon-work'})
            
            for link in all_links:
                href = link['href']
                if href:
                    data = requests.get(href)
                    soup = BeautifulSoup(data.text)
                    div_text_company = soup.find('p', {'class': 'font-text-18'})
                    findjob = soup.find('div', {'class': 'col-md-8 col-sm-8 col-xs-6'})
                    
                    if div_text_company and findjob:
                        company = div_text_company.find('a')
                        position = findjob.find('h1', {'class': 'margin-bottom text-red font-size-20'})
                    else:
                        div_col_12 = soup.find('div', {'class': 'col-12'})
                        findjob = soup.find('div', {'class': 'borderStyle borderRadiusStyle p-3'})
                        
                        if div_col_12 and findjob:
                            company = div_col_12.find('p', {'class': 'textRed fontSubHead font-DB-HeaventRounded-Bold'})
                            position = findjob.find('p', {'class': 'textRed font-text-20 font-DB-HeaventRounded-Bold'})
                    
                    if company and position:
                        name_company = company.text
                        name_position = position.text
                        pattern = re.compile(r'[\u4e00-\u9fff]+')
                        cleaned_text = pattern.sub('', name_position)
                        
                        # Combine translation of both name_position and name_company
                        translation = GoogleTranslator(source="auto", target="en").translate(cleaned_text)
                        
                        position_list.append(translation)
                        company_list.append(name_company)
                        
                        if soup.find('div',{'class':'clWhitetGray borderRadiusStyle p-3 mb-3'}):
                            element = soup.find('div',{'class':'clWhitetGray borderRadiusStyle p-3 mb-3'})
                            elementA = element.find('span',{'class':'textRed'})
                            elementB = elementA.text
                            elementC = elementB.replace(',','')
                            elementD = int(elementC)
                            if elementD == 0:
                                elementD = 0
                            elif elementD <= 5:
                                elementD = 1
                            elif elementD <= 10:
                                elementD = 2
                            elif elementD <= 50:
                                elementD = 3
                            elif elementD <= 100:
                                elementD = 4
                            elif elementD <= 500:
                                elementD = 5
                            elif elementD <= 1000:
                                elementD = 6
                            elif elementD <= 5000:
                                elementD = 7
                            elif elementD <= 10000:
                                elementD = 8
                            elif elementD <= 50000:
                                elementD = 9
                            else:
                                elementD = 10
                            
                        else:
                            a = soup.find('div',{'class':'col-md-4 col-sm-4 col-xs-12 hidden-xs'})
                            line2 = a.find_all('span',{'class':'text-red'})
                            elementA = line2[1]
                            elementB =  elementA.text
                            elementC = elementB.replace(',','')
                            elementD = int(elementC)
                            if elementD == 0:
                                elementD = 0
                            elif elementD <= 5:
                                elementD = 1
                            elif elementD <= 10:
                                elementD = 2
                            elif elementD <= 50:
                                elementD = 3
                            elif elementD <= 100:
                                elementD = 4
                            elif elementD <= 500:
                                elementD = 5
                            elif elementD <= 1000:
                                elementD = 6
                            elif elementD <= 5000:
                                elementD = 7
                            elif elementD <= 10000:
                                elementD = 8
                            elif elementD <= 50000:
                                elementD = 9
                            else:
                                elementD = 10
                            
                        visitors_list.append(elementD)

            print('complete link number:', page)
            page += 1

        table = pd.DataFrame([position_list, company_list, visitors_list]).transpose()
        table.columns = ['position', 'company', 'rating']
        table.set_index('position', inplace=True)  # Use inplace=True to modify the DataFrame in place

        connection_string = 'DRIVER={SQL Server};SERVER=DESKTOP-UJ5T3UB\\SQLEXPRESS;DATABASE=Jobbkk;Trusted_Connection=yes;'
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        # Insert data into the SQL Server table
        for i in range(len(position_list)):
            Position = position_list[i]
            Company = company_list[i]
            Rating = visitors_list[i]
            
            # Get the current date and time
            Currentdate = datetime.now()

            # Assuming your table has columns 'Position_Name', 'Company_Name', 'Rating', and 'CreatedDate'
            sql_query = "INSERT INTO JobTable (Position, Company, Rating, Currentdate) VALUES (?, ?, ?, ?)"
            cursor.execute(sql_query, Position, Company, Rating, Currentdate)

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        # Save the DataFrame to an Excel file
        # table = pd.DataFrame({'position': position_list, 'company': company_list, 'rating': visitors_list})
        # table.set_index('position', inplace=True)
        # table.to_excel('NewPosition05.xlsx', engine='openpyxl')

        return {'status': 'success'}

def job():
    page = 3
    JobScraper().get(page)

# Schedule the job to run every 3 days
schedule.every(3).days.do(job)

if __name__ == '__main__':
    # Run the job immediately when the program starts
    job()

    while True:
        schedule.run_pending()
        time.sleep(1)


