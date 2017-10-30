
# coding: utf-8

# ### 로또번호 추정하여 만들기 순서
# 1. 로또 홈페이지 크롤링
# 2. 최근 당첨번호 트랜드 분석
# 3. 번호 선정 로직 생성하기
# 4. random하게 번호 뽑기
# 4. 번호 선정후 1~45 경우수와 (결과)선정된 번호의 경우수 비교하기
# 5. 생성시마다 10개번호 산출

# <font color='red'>
#     <ul>
#         <li>1자리~6자리 합계 정규분포에서 상위 95%, 하위 5% 수준으로 분석시 max=188, min=84. 6개 숫자 합의 범위 188 ~ 84로 제한함(정규분포 90%만 인정)</li>
#         <li>홀수, 짝수 조합분석시 6개모두 홀수, 짝수 일 경우수는  1.82% 임으로 6개모두 짝/홀수 경우는 제외</li>
#         <li>color band는 3개 또는 4개 조합이 가장 높음.</li>
#         <li>연속번호 당첨 1,2조합, 1,2,3조합만.</li>
#         <li>동일한 끝자리수가 3회 이상인 조합은 버림 </li>
#     </ul>
# </font>

# <head>mysql> describe winlotto;</head>
# <pre>
# +------------+-------------+------+-----+---------+-------+
# | Field      | Type        | Null | Key | Default | Extra |
# +------------+-------------+------+-----+---------+-------+
# | count      | int(10)     | NO   |     | NULL    |       |
# | 1          | int(2)      | NO   |     | NULL    |       |
# | 2          | int(2)      | NO   |     | NULL    |       |
# | 3          | int(2)      | NO   |     | NULL    |       |
# | 4          | int(2)      | NO   |     | NULL    |       |
# | 5          | int(2)      | NO   |     | NULL    |       |
# | 6          | int(2)      | NO   |     | NULL    |       |
# | 7          | int(2)      | NO   |     | NULL    |       |
# | persons    | int(2)      | NO   |     | NULL    |       |
# | amounts    | varchar(20) | NO   |     | NULL    |       |
# | total      | int(5)      | NO   |     | NULL    |       |
# | odd        | int(2)      | NO   |     | NULL    |       |
# | even       | int(2)      | NO   |     | NULL    |       |
# | yellow     | int(2)      | NO   |     | NULL    |       |
# | blue       | int(2)      | NO   |     | NULL    |       |
# | red        | int(2)      | NO   |     | NULL    |       |
# | green      | int(2)      | NO   |     | NULL    |       |
# | gray       | int(2)      | NO   |     | NULL    |       |
# | band       | int(2)      | NO   |     | NULL    |       |
# | 1continue  | int(2)      | NO   |     | NULL    |       |
# | 2continue  | int(2)      | NO   |     | NULL    |       |
# | 3continue  | int(2)      | NO   |     | NULL    |       |
# | 4continue  | int(2)      | NO   |     | NULL    |       |
# | endigDigit | int(2)      | NO   |     | NULL    |       |
# +------------+-------------+------+-----+---------+-------+
#  </pre>
# <pre>
# mysql> select max(total), min(total) from winlotto where band=5 and count > 677;
# +------------+------------+
# | max(total) | min(total) |
# +------------+------------+
# |        177 |        122 |
# +------------+------------+
# 1 row in set (0.00 sec)
#
# mysql> select max(total), min(total) from winlotto where band=4 and count > 677;
# +------------+------------+
# | max(total) | min(total) |
# +------------+------------+
# |        198 |         87 |
# +------------+------------+
# 1 row in set (0.00 sec)
#
# mysql> select max(total), min(total) from winlotto where band=3 and count > 677;
# +------------+------------+
# | max(total) | min(total) |
# +------------+------------+
# |        203 |         50 |
# +------------+------------+
# 1 row in set (0.00 sec)
#
# mysql> select max(total), min(total) from winlotto where band=2 and count > 677;
# +------------+------------+
# | max(total) | min(total) |
# +------------+------------+
# |        193 |         73 |
# +------------+------------+
# 1 row in set (0.00 sec)
# </pre>

#lotto.py

import requests
from bs4 import BeautifulSoup
import mysql.connector
import sqlalchemy
from sqlalchemy import create_engine
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import random

#웹 크롤링 한 결과를 저장할 리스트
lotto_list = []

#로또 웹 사이트의 첫 주소
main_url = "http://www.nlotto.co.kr/gameResult.do?method=byWin"

#웹 크롤릴 주소
basic_url = "http://www.nlotto.co.kr/gameResult.do?method=byWin&drwNo="

def getLast():
    resp = requests.get(main_url)
    soup = BeautifulSoup(resp.text, "lxml")
    line = str(soup.find("meta", {"id" : "desc", "name" : "description"})['content'])

    begin = line.find(" ")
    end = line.find("회")

    if begin == -1 or end == -1:
        print("not found last lotto number")
        exit()
    return int(line[begin + 1 : end])

def checkLast():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    sql = "SELECT MAX(count) FROM winlotto"

    try:
        count = connector.execute(sql)
        result = count.fetchone()
        if result[0] is None:
            result = [1,]

    except Exception as err:
        print(str(err))

    connector.close()

    return result[0]

def crawler(fromPos,toPos):
    for i in range(fromPos,toPos + 1):
        crawler_url = basic_url + str(i)

        resp = requests.get(crawler_url)
        soup = BeautifulSoup(resp.text, "lxml")
        '''
        개발자 모드로 분석하여 HTML Tag로 찾을때
        div_data = soup.find_all('div', class_='lotto_win_number mt12')
        p_data = div_data[0].find_all('p',class_='number')
        img_number = p_data[0].find_all('img')
        '''
        line = str(soup.find("meta", {"id" : "desc", "name" : "description"})['content'])
        print("당첨회차: " + str(i))

        begin = line.find("당첨번호")
        begin = line.find(" ", begin) + 1
        end = line.find(".", begin)
        numbers = line[begin:end]
        print("당첨번호: " + numbers)

        begin = line.find("총")
        begin = line.find(" ", begin) + 1
        end = line.find("명", begin)
        persons = line[begin:end]
        print("당첨인원: " + persons)

        begin = line.find("당첨금액")
        begin = line.find(" ", begin) + 1
        end = line.find("원", begin)
        amount = line[begin:end]
        print("당첨금액: " + amount)

        info = {}
        info["회차"] = i
        info["번호"] = numbers
        info["당첨자"] = persons
        info["금액"] = amount

        lotto_list.append(info)

def insert():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    for dic in lotto_list:
        count = dic["회차"]
        numbers = dic["번호"]
        persons = dic["당첨자"]
        amounts = dic["금액"]
        odd = 0  # 홀수
        even = 0  # 짝수
        yellow = 0  # 1~10
        blue = 0  # 11~20
        red = 0  # 21~30
        green = 0  # 31~40
        gray = 0  # 41 ~ 45
        band = 0  #숫자 밴드 카운트
        winNumbers = []
        lotto_continue = 0
        lotto_2continue = 0
        lotto_3continue = 0
        lotto_4continue = 0

        print("insert to database at " + str(count))
        numberlist = str(numbers).split(",")

        winNumbers.append(int(numberlist[0]))
        winNumbers.append(int(numberlist[1]))
        winNumbers.append(int(numberlist[2]))
        winNumbers.append(int(numberlist[3]))
        winNumbers.append(int(numberlist[4]))
        winNumbers.append(int(numberlist[5].split("+")[0]))
        winNumbers.append(int(numberlist[5].split("+")[1]))

        persons = int(persons)
        total = sum(winNumbers[0:6])

        # 홀수갯수 구하기
        for i in range(0,6):
            if (winNumbers[i] % 2 != 0):
                odd = odd + 1;
        even = 6 - odd  # 짝수갯수는 6 - 홀수갯수

        # bamd 구분하기
        for i in range(0,6):
            if (winNumbers[i] <= 10):
                yellow += 1
            elif (winNumbers[i] >= 11 and winNumbers[i] <= 20):
                blue += 1
            elif (winNumbers[i] >= 21 and winNumbers[i] <= 30):
                red += 1
            elif (winNumbers[i] >= 31 and winNumbers[i] <= 40):
                green += 1
            elif (winNumbers[i] >= 41 and winNumbers[i] <= 45):
                gray += 1
        if (yellow > 0):
            band += 1
        if (blue > 0):
            band += 1
        if (red > 0):
            band += 1
        if (green > 0):
            band += 1
        if (gray > 0):
            band += 1

        #continure number 구하기
        #1 연번
        if (winNumbers[1] - winNumbers[0] == 1):
            lotto_continue += 1
        elif (winNumbers[2] - winNumbers[1] == 1):
            lotto_continue += 1
        elif (winNumbers[3] - winNumbers[2] == 1):
            lotto_continue += 1
        elif (winNumbers[4] - winNumbers[3] == 1):
            lotto_continue += 1
        elif (winNumbers[5] - winNumbers[4] == 1):
            lotto_continue += 1

        #2 연번
        if (winNumbers[2] - winNumbers[0] == 2):
            lotto_2continue += 1
            lotto_continue -= 1
        elif (winNumbers[3] - winNumbers[1] == 2):
            lotto_2continue += 1
            lotto_continue -= 1
        elif (winNumbers[4] - winNumbers[2] == 2):
            lotto_2continue += 1
            lotto_continue -= 1
        elif (winNumbers[5] - winNumbers[3] == 2):
            lotto_2continue += 1
            lotto_continue -= 1

        #3 연번
        if (winNumbers[3] - winNumbers[0] == 3):
            lotto_3continue += 1
            lotto_2continue -= 1
        elif (winNumbers[4] - winNumbers[1] == 3):
            lotto_3continue += 1
            lotto_2continue -= 1
        elif (winNumbers[5] - winNumbers[2] == 3):
            lotto_3continue += 1
            lotto_2continue -= 1

        #4 연번
        if (winNumbers[4] - winNumbers[0] == 4):
            lotto_4continue += 1
            lotto_3continue += 1
        elif (winNumbers[5] - winNumbers[1] == 4):
            lotto_4continue += 1
            lotto_3continue += 1

        #끝자리수 횟수 확인
        ending_digit = []

        for i in range(0,6):
            if (winNumbers[i] <= 9):
                ending_digit.append(winNumbers[i])
            elif (winNumbers[i] >= 10 and winNumbers[i] <= 19):
                ending_digit.append(winNumbers[i] - 10)
            elif (winNumbers[i] >= 20 and winNumbers[i] <= 29):
                ending_digit.append(winNumbers[i] - 20)
            elif (winNumbers[i] >= 30 and winNumbers[i] <= 39):
                ending_digit.append(winNumbers[i] - 30)
            elif (winNumbers[i] >= 40 and winNumbers[i] <= 45):
                ending_digit.append(winNumbers[i] - 40)
        unique_elements, counts_elements = np.unique(ending_digit, return_counts=True)
        max_ending_digit_count = int(max(counts_elements))  # max count

        # 아래 코드를 사용하면 sql문 에러 발생으로 시행되지 않음
        # sql = "INSERT INTO winlotto (count, 1, 2, 3, 4, 5, 6, 7, persons, amounts)\
        #        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        # connector.execute(sql, count, i1, i2, i3, i4, i5, i6, 7, persons, amounts)


        # sql문 생성시 table name 으로 표기함.
        sql = "INSERT INTO winlotto VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

        try:
            connector.execute(sql, count,winNumbers[0], winNumbers[1],winNumbers[2],winNumbers[3],winNumbers[4],\
            winNumbers[5],winNumbers[6],persons, amounts, total, odd, even,yellow, blue, red, green, gray, band,\
                              lotto_continue, lotto_2continue, lotto_3continue, lotto_4continue, max_ending_digit_count)
        except Exception as err:
            print(str(err))
            break

    connector.close()

def analysis_max():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    #각 자리수별 뽑힌 숫자들 전체를 조회
    for i in range(1,8):
        sql = "select `"
        sql += str(i)
        sql += "` from winlotto"

        try:
            nums = connector.execute(sql)
            results = nums.fetchall()

            #해당 숫자의 뽑힌 횟수를 하나씩증가
            lottoarray = [0 for i in range(46)]
            for row in results:
                k = row[0]
                count = lottoarray[k]
                lottoarray[k] = count + 1
            print (i, "자리 max count 숫자 =", lottoarray.index(max(lottoarray)))
        except Exception as err:
            print(str(err))

    connector.close()

def analysis(time, band=3):
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    #1부터 45까지의 배열을 생성하고 0으로 초기화
    lottoarray = [0 for i in range(0,46)]

    #각 자리수별 뽑힌 숫자들 전체를 조회
    for i in range(1,7):
        sql = "select `"
        sql += str(i)
        sql += "` from winlotto where count > {} and band = {}".format(time,band)

        try:
            nums = connector.execute(sql)
            results = nums.fetchall()
            #해당 숫자의 뽑힌 횟수를 하나씩증가

            for row in results:
                k = row[0]
                count = lottoarray[k]
                lottoarray[k] = count + 1

        except Exception as err:
            print(str(err))

    print ("전체 숫자 당첨 카운수")
    for i in range(1, len(lottoarray)):
        if (i % 10) == 0:
                print("")  # 10개 마다 줄 바꾸기
        print("[" + str(i) + ":" + str(lottoarray[i]) + "]", end=" ")
    print("")
    connector.close()

    return (lottoarray)

def sum_analysis(count_times):
    # 100회 기간 분석
    last_time = checkLast()
    start_time = last_time - count_times

    # db접속
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()
    # band=3,4에 대해서 구함
    df = pd.read_sql("SELECT total FROM winlotto WHERE count > {} and band = 3 or band = 4".format(start_time), con = connector)
    sum = df.values
    # print ('max = ', max(sum), 'min = ', min(sum))

    # print ('상,하위 분위수별 수 quantile 0.95 = ', quantile(sum, 0.95), 'quantile 0.05 = ', quantile(sum, 0.05))
    # quantileCount = count(sum, quantile(sum, 0.95),quantile(sum, 0.05))  # 퍼센티지 구하기
    # print ("회수별 sum대비 분위수의 점유율 = ","%3.2f" %(quantileCount/len(sum)))

    # print ('상,하위 분위수별 수 quantile 0.90 = ', quantile(sum, 0.90), 'quantile 0.1 = ', quantile(sum, 0.1))
    # quantileCount = count(sum, quantile(sum, 0.90),quantile(sum, 0.1))  # 퍼센티지 구하기
    # print ("회수별 sum대비 분위수의 점유율 = ","%3.2f" %(quantileCount/len(sum)))
    # print ("")

    # plt.figure(figsize=(18,10))
    # plt.hist(sum, bins=35, facecolor='red', alpha=0.4, histtype='stepfilled')
    # plt.hist(sum, bins=40, facecolor='green', alpha=0.4, histtype='stepfilled')
    # plt.hist(sum, bins=45, facecolor='black', alpha=0.4, histtype='stepfilled')
    # plt.xlabel('sum')
    # plt.ylabel('count')
    # plt.show()
    connector.close()

    return (quantile(sum, 0.90), quantile(sum, 0.1))

def oddEven():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    df = pd.read_sql("select odd from winlotto WHERE count > 600", con = connector)
    odd = df.values
    unique_elements, counts_elements = np.unique(odd, return_counts=True)
    print ("당첨번호 6개중 홀수 번호가 나온 총 갯수")
    print (np.asarray((unique_elements,counts_elements)), "전체회차 = ", len(odd))

    df = pd.read_sql("select even from winlotto WHERE count > 600", con = connector)
    even = df.values
    unique_elements, counts_elements = np.unique(even, return_counts=True)
    print ("당첨번호 6개중 짝수 번호가 나온 총 갯수")
    print (np.asarray((unique_elements,counts_elements)), "전체회차 = ", len(even))
    print ()

    plt.figure(figsize=(18,10))
    plt.hist(odd, bins=6)
    # plt.hist(even, bins=6)

    connector.close()


def count(sum, maxi, mini):
    count = 0

    for num in sum:
        if (num >= mini and num <= maxi):
            count += 1
    return count

def quantile(x,p):
    p_index = int(p * len(x))
    return sorted(x)[p_index]

def mean(x, y):
    return sum(y) / len(x)

def bandCount():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    # band = pd.read_sql("select band from winlotto", con = connector)
    band = pd.read_sql("select band from winlotto where count > 677", con = connector)

    unique_elements, counts_elements = np.unique(band, return_counts=True)
    print ("컬러별 밴드의 수")
    print (np.asarray((unique_elements,counts_elements)), "전체회차 = ", len(band))
    print ("")

    plt.figure(figsize=(18,10))
    plt.hist(band.values)
    # plt.show()

    connector.close()

def used_number(count):
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    courrentCount = pd.read_sql("SELECT max(count) FROM winlotto", con = connector)
    beginCount = courrentCount - count
    begin = int(beginCount.iloc[0])

    used = pd.read_sql("SELECT `1`,`2`,`3`,`4`,`5`,`6` FROM winlotto WHERE count >= %s" %begin, con = connector)
    used = np.unique(used)

    print ('조회한 회차수 = ', count)
    print ('사용할 번호는 = ', used)
    print ('사용할 번호 갯수는 = ', len(used))
    print ()

    connector.close()
    return used

# generate된 숫자를 가지고 total/6=나머지 번호를 가지고 숫자 제외,포함
def remainder(result):
    re = True
    div6_even = 1
    div6_odd = 0
    # 6개 숫자 합을 구한 6으로 나누어 일자리 숫자구하기
    div6 = round(sum(result[0:6]) / 6)

    if (div6 % 2 != 0):
        div6_even = 0  # etc_eo는 etc_even odd를 뜻함.
    else:
        div6_odd = 1  # 홀수는 1로 세팅

    # 홀,짝수 갯수 구하기
    odd = 0
    for i in range(0,6):
        if (result[i] % 2 != 0):
            odd = odd + 1
    even = 6 - odd

    # odd, even 결과로 아래와 같은 숫자 조합 검증
    if odd == 6:  # odd 6개 번호는 인정하지 않음.
        re = False

    if even == 6:  # even 6개 번호는 인정하지 않음.
        re = False

    if odd == 5:
        if div6_even == 0:
            # 홀수가 5개이고 total/6=나머지가 짝수이면 false를 return하여 다시 generate함
            re = False
        else:
            re = True

    if even == 5:
        if div6_odd == 1:
            # 짝수가 5개이고 total/6=나머지가 홀수이면 false를 return하여 다시 generate함
            re = False
        else:
            re = True

    return re

def generate(targetBand, numlist, quantile_max, quantile_min):
    ConditionCount = 0
    lotto_continue = 0
    # numlist = set(numlist)
    winNumber = []
    gen_count = 0
    result = 0  # 난수 발생후 저장변수 0으로 초기화
    # 제외건수
    drop = 0
    drop2 = 0
    drop3 = 0
    drop4 = 0

    while True:  # 예측 조합 추출후 break로 종료
        band = 0  #숫자 밴드 카운트
        lotto_continue = 0  # 연번 변수 0으로 초기화
        # band 구하기
        yellow = 0  # 1~10
        blue = 0  # 11~20
        red = 0  # 21~30
        green = 0  # 31~40
        gray = 0  # 41 ~ 45


        result = sorted(random.sample(numlist,6))  # 예측번호로 부터 6개 뽑아내기

        # band 구분하기
        for i in range(0,6):
            if (result[i] <= 10):
                yellow += 1
            elif (result[i] >= 11 and result[i] <= 20):
                blue += 1
            elif (result[i] >= 21 and result[i] <= 30):
                red += 1
            elif (result[i] >= 31 and result[i] <= 40):
                green += 1
            elif (result[i] >= 41 and result[i] <= 45):
                gray += 1

        #band 카운트
        if (yellow > 0):  band += 1
        if (blue > 0):  band += 1
        if (red > 0):   band += 1
        if (green > 0): band += 1
        if (gray > 0):  band += 1

        # sum 점수 구하기
        total = sum(result[0:6])

        #3자리 연번이상 확인하기
        if (result[3] - result[0] == 3):  #4 연번
            lotto_continue += 1
        elif (result[4] - result[1] == 3):
            lotto_continue += 1
        elif (result[5] - result[2] == 3):
            lotto_continue += 1
        elif (result[4] - result[0] == 4):  #5 연번
            lotto_continue += 1
        elif (result[5] - result[1] == 4):
            lotto_continue += 1

        # 모든 조건을 검증후 번호 추출
        # if (odd < 5) and (even < 5):  # 홀짝/짝수 5개 이상 조합 제외
        if (targetBand == band):  # 3,4 밴드등 목표 밴드 확인
            if (total <= quantile_max) and (total >= quantile_min):  # 분위수 range외 제외
                if (lotto_continue == 0):  #4,5 연속번호 조합은 제외
                    ConditionCount += 1
                    if (ConditionCount > random.randint(100000,1000000)):  #십만에서 백만중 하나 추출하여 count횟수가 그만큼 클때 인정
                        if remainder(result):  # total/6 끝수 판단하기
                            winNumber.append(result)
                            ConditionCount = 0  # 0으로 초기화
                            lotto_continue = 0
                            gen_count += 1
                            print ("remainder=",drop)
                            print ("continue=",drop2)
                            print ("quantile=",drop3)
                            print ("band=",drop4)
                            print ("")
                        else:  drop += 1
                else:  drop2 += 1
            else:  drop3 += 1
        else:  drop4 += 1

        if gen_count > 4:
            break

    return winNumber

def continue_number():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    numbers = pd.read_sql("SELECT `1continue`,`2continue`,`3continue`,`4continue` FROM winlotto", con = connector)

    plt.plot(numbers)

    unique_elements, counts_elements = np.unique(numbers, return_counts=True)
    print ("연번의 합계")
    print (np.asarray((unique_elements,counts_elements)), "전체회차 = ", len(numbers))
    print ()

    connector.close()

def to_csv():
    pwd = 'rlaehgus1'
    engine = create_engine('mysql+mysqlconnector://root:'+pwd+'@localhost/lotto', echo=False)
    connector = engine.connect()

    df = pd.read_sql("SELECT * FROM winlotto", con = connector)
    df.to_csv("winlotto.csv", index=False)
    connector.close()

# In[6]:

def main():
    # 최신 추첨 회차 확인
    last_time = getLast()
    dblast_time = checkLast()

    #신규 회차확인시 크롤링
    if dblast_time < last_time:
        print("최신 회차는 " + str(last_time) + " 회 이며, 데이터베이스에는 " + str(dblast_time) + "회 까지 저장되어 있습니다.")
        print("업데이트를 시작합니다.")
        crawler(dblast_time, last_time)

    #신규 회차 있을때 db update
    if len(lotto_list) > 0:
        insert()

    # ---know-how 여기서 부터 사용할 번호를 선택하는 방법--- #
    b3_nums = []
    b4_nums = []
    count_times = 100  # 최근 100회를 분석

    # band=3,4에 대한 quantiel 10%로 max, min 값을 구함
    quantile = sum_analysis(count_times)
    quantile_max = quantile[0]
    quantile_min = quantile[1]
    print ("최근 {}회차 sum max 는 ".format(count_times),quantile_max, "sum min은 ",quantile_min)

    # band=4 최근 25회중 나오지 않는 번호는 제외
    # band=3 최근 50회중 나오지 않는 번호는 제외
    for band in [3,4]:
        if band == 3:
            time_index = 50
            nums = analysis(last_time - time_index, band)
            except_nums = []
            for j in range(1,46):
                if nums[j] != 0:
                    b3_nums.append(j)
                else:
                    except_nums.append(j)
        elif band == 4:
            time_index = 25
            nums = analysis(last_time - time_index, band)
            except_nums = []
            for j in range(1,46):
                if nums[j] != 0:
                    b4_nums.append(j)
                else:
                    except_nums.append(j)

        print ("band{}, {}회 추첨중 zero count {}가 제외됨".format(band, time_index, except_nums))
        print ("")

    # 3, 4밴드 조합으로 추출
    for band in (3,4):
        if band == 3:
            winNumber = generate(band, b3_nums, quantile_max, quantile_min)  #generate 함수 호출
        elif band == 4:
            winNumber = generate(band, b4_nums, quantile_max, quantile_min)  #generate 함수 호출
        # 번호생성후 각 번호 조합 출력
        for r in range(0,len(winNumber)):
            print ("target_band = {}, win numbers = {}".format(band, winNumber[r]))

    '''
    # 연번호 확인하기
    continue_number()

    #자리별 count
    bandCount()

    # 홀수, 짝수 회차별 갯수 확인
    oddEven()

    # 자리수별 max number
    analysis_max()

    #1~45 숫자 출현 횟수
    analysis(last_time-100)

    #정해진 기간의 회차별 sum 분포를 구하고, max, min를 95%, 90% 수준으로 구함
    sum_analysis()

    # mysql db내용을 csv로 저장하기
    def to_csv()
    '''
if __name__ == "__main__":
    main()
