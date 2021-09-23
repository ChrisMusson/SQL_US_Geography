# Introduction

I have done lots of SQL exercises and quizzes, and so have had lots of practice at writing queries. However, these exercises very rarely require you to think about how you would structure a database yourself, or even consider problems you might face when given imperfect data. For this reason, I decided to take a dive into some datasets based on US geography and see what happens.

# Data
I downloaded these two datasets from kaggle:

[US ZIP Codes with latitude and longitude](https://www.kaggle.com/joeleichter/us-zip-codes-with-lat-and-long/version/1)

[US Population By ZIP Code](https://www.kaggle.com/census/us-population-by-zip-code?select=population_by_zip_2010.csv)

and I modified the data from this website so that the given ZIP codes were also present in the two datasets above.

[US State Capitals](http://thrandur.net/chitchat/us-states-capitals-and-a-zip-code/)

The `US State Capitals` and `US ZIP Codes with latitude and longitude` CSVs will be hosted on the GitHub page, but the other file is quite large so it will have to be downloaded directly from kaggle.

# Getting Started

First of all, this data needs to be loaded into a database - I will be using MySQL.

```SQL
CREATE DATABASE us_zip_codes;
USE us_zip_codes;

-- zip_code is always 5 digits but potentially starting with a 0, so used a CHAR to avoid any future difficulties.
-- It will also not repeat in this dataset so can be used as a primary key
-- longitude and latitude go between +-180 and can be followed by 6 decimal places
CREATE TABLE Location (
    zip_code CHAR(5) NOT NULL PRIMARY KEY,
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6)
);

-- if you are copying along with the queries, note that you will have to change these filepaths
LOAD DATA LOCAL INFILE 'C:/Users/Chris/Dev/US_ZIP/zip_lat_long.csv'
INTO TABLE Location
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(zip_code, latitude, longitude);

-- ZIP Code will repeat here so can't use that for primary key
-- It's unclear how or even if a primary key will be helpful but it won't hurt
CREATE TABLE Population (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    zip_population INT,
    minimum_age INT,
    maximum_age INT,
    gender VARCHAR(6),
    zip_code CHAR(5)
);

LOAD DATA LOCAL INFILE 'C:/Users/Chris/Dev/US_ZIP/population_by_zip_2010.csv'
INTO TABLE Population
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(zip_population, minimum_age, maximum_age, gender, zip_code, @ignore);

CREATE TABLE Capitals (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    state_long VARCHAR(32),
    state_short VARCHAR(2),
    capital VARCHAR(32),
    zip_code CHAR(5)
);

LOAD DATA LOCAL INFILE 'C:/Users/Chris/Dev/US_ZIP/state_capitals.csv'
INTO TABLE Capitals
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(state_long, state_short, capital, zip_code);
```

#

Now, just to make sure there aren't any obvious problems, I will just see what the total population is from the `Population` table and make sure it makes sense

```SQL
SELECT SUM(s) AS total_population
FROM (
    SELECT SUM(zip_population) AS s
    FROM Population
    GROUP BY zip_code
) x;
```

```
+------------------+
| total_population |
+------------------+
|        937333281 |
+------------------+
```
Oh dear. It might be a good idea to take a look at one particular ZIP Code and see if that sheds some light on why it's so far out.

```SQL
SELECT * FROM Population WHERE zip_code = 90210;
```

```
+---------+----------------+-------------+-------------+--------+----------+
| id      | zip_population | minimum_age | maximum_age | gender | zip_code |
+---------+----------------+-------------+-------------+--------+----------+
|  199664 |            491 |          62 |          64 | female | 90210    |
|  224105 |          21741 |           0 |           0 |        | 90210    | <<
|  289986 |            591 |           5 |           9 | male   | 90210    |
|  304665 |            871 |          55 |          59 | female | 90210    |
-----------------------39 more normal-looking entries-----------------------
| 1092168 |            873 |          50 |          54 | female | 90210    |
| 1100549 |            582 |           5 |           9 | female | 90210    |
| 1140258 |          10292 |           0 |           0 | male   | 90210    | <<
| 1270600 |            451 |          35 |          39 | male   | 90210    |
| 1412337 |          11449 |           0 |           0 | female | 90210    | <<
| 1420651 |            364 |          67 |          69 | male   | 90210    |
+---------+----------------+-------------+-------------+--------+----------+
```

It looks like everyone is being triple counted as there are rows for the different age ranges as expected, but then there are also rows for total female, total male, and total overall populations for the `zip_code`. To exclude those rows, I can just exclude the rows where `minimum_age` and `maximum_age` are both equal to 0.

With that in mind,

```SQL
SELECT SUM(s) AS total_population
FROM (
    SELECT SUM(zip_population) AS s
    FROM Population
    WHERE NOT (minimum_age = 0 AND maximum_age = 0)
    GROUP BY zip_code
) x;
```

```
+------------------+
| total_population |
+------------------+
|        312444427 |
+------------------+
```

This looks a lot more likely. A [quick google](https://www.google.com/search?q=us+population+census+2010) of the official census figures seems to show that this is a bit of an overestimation, but it's only a 1.2% difference and I don't know how perfect this dataset is, so I am just not going to worry about it and carry on.

It might get tedious and confusing having to filter out the multiple counts of population when I get on to more complex queries, so I will create a view that excludes them and use that from now on.

```SQL
CREATE VIEW cleaned_population AS
SELECT * FROM Population
WHERE NOT (minimum_age = 0 AND maximum_age = 0);
```

And to confirm it has worked:

```SQL
SELECT SUM(zip_population) AS total_population FROM cleaned_population;
```

```
+------------------+
| total_population |
+------------------+
|        312444427 |
+------------------+
```

Perfect.

Unfortunately, MySQL doesn't have a `PIVOT` function, but I can still see the breakdown of population by gender by running

```SQL
SELECT
    SUM(CASE WHEN gender = "male" THEN zip_population END) AS male,
    SUM(CASE WHEN gender = "female" THEN zip_population END) AS female
FROM cleaned_population;
```

```
+-----------+-----------+
| male      | female    |
+-----------+-----------+
| 153550999 | 158893428 |
+-----------+-----------+
```

This result is quite surprising to me, as the natural gender birth ratio is estimated to be roughly 1.05:1 in favour of males.

My hypothesis would have been that there are more males at younger ages, but the number of females would overtake the number of males as time progresses, mainly due to their longer life expectancy.

I was very confused for a while here because in order to see if there are more young males than females, I tried executing this

```SQL
SELECT
    SUM(CASE WHEN gender = "male" AND maximum_age <= 10 THEN zip_population END) AS male,
    SUM(CASE WHEN gender = "female" AND maximum_age <=10 THEN zip_population END) AS female
FROM cleaned_population;
```

but got the following result

```
+----------+----------+
| male     | female   |
+----------+----------+
| 22758889 | 23808779 |
+----------+----------+
```

I really thought my hypothesis was just incorrect, but it was only when I looked at the dataset a bit more that I saw the problem. I realised that the 85+ age group has a maximum age of 0, so they were contributing to the above total. If my hypothesis was correct and there are more females at older ages, then this would make these totals heavily skewed towards them.

To see how it should have looked, I needed to either add a condition to each case that the maximum age couldn't be equal to 0, or to just use the minimum_age instead.

```SQL
SELECT
    SUM(CASE WHEN gender = "male" AND minimum_age <= 10 THEN zip_population END) AS male,
    SUM(CASE WHEN gender = "female" AND minimum_age <= 10 THEN zip_population END) AS female
FROM cleaned_population;
```

```
+----------+----------+
| male     | female   |
+----------+----------+
| 31662354 | 30293731 |
+----------+----------+
```

This is much more in line with expectations. To get a full look at how the ratio of males to females changes with age, I did this:

```SQL
SELECT *, male / female AS ratio
FROM (
    SELECT 
        minimum_age, maximum_age,
        SUM(CASE WHEN gender = 'male' THEN s END) as male,
        SUM(CASE WHEN gender = 'female' THEN s END) as female
        FROM(
            SELECT
                gender,
                minimum_age,
                maximum_age,
                SUM(zip_population) AS s
            FROM
                cleaned_population
            GROUP BY
                minimum_age, gender
            ORDER BY minimum_age
        ) AS x
    GROUP BY minimum_age
) AS y;
```

```
+-------------+-------------+----------+----------+--------+
| minimum_age | maximum_age | male     | female   | ratio  |
+-------------+-------------+----------+----------+--------+
|           0 |           4 | 10433913 |  9990840 | 1.0443 |
|           5 |           9 | 10512119 | 10075101 | 1.0434 |
|          10 |          14 | 10716322 | 10227790 | 1.0478 |
|          15 |          17 |  6742256 |  6380686 | 1.0567 |
|          18 |          19 |  4704829 |  4494577 | 1.0468 |
|          20 |          20 |  2337410 |  2239410 | 1.0438 |
|          21 |          21 |  2249738 |  2157158 | 1.0429 |
|          22 |          24 |  6555954 |  6304741 | 1.0398 |
|          25 |          29 | 10752650 | 10591022 | 1.0153 |
|          30 |          34 | 10114884 | 10093295 | 1.0021 |
|          35 |          39 | 10156901 | 10262228 | 0.9897 |
|          40 |          44 | 10507832 | 10623539 | 0.9891 |
|          45 |          49 | 11323485 | 11631245 | 0.9735 |
|          50 |          54 | 11042855 | 11493287 | 0.9608 |
|          55 |          59 |  9625056 | 10261711 | 0.9380 |
|          60 |          61 |  3464396 |  3736167 | 0.9273 |
|          62 |          64 |  4712427 |  5121581 | 0.9201 |
|          65 |          66 |  2555908 |  2838880 | 0.9003 |
|          67 |          69 |  3376309 |  3838537 | 0.8796 |
|          70 |          74 |  4305348 |  5108343 | 0.8428 |
|          75 |          79 |  3225751 |  4192271 | 0.7695 |
|          80 |          84 |  2321799 |  3488181 | 0.6656 |
|          85 |           0 |  1812857 |  3742838 | 0.4844 |
+-------------+-------------+----------+----------+--------+
```
Finally, it can be seen that the ratio follows a trend goes perfectly with my hypothesis

#

Next up, I want to find out where the most populous ZIP Codes are located. I will need to take into consideration that some ZIP Codes might appear in one dataset but not the other, so will have to exclude them.

I will first update my view of the `Population` table so that I don't need to keep writing such a long query out to get the total population for each ZIP Code.

```SQL
ALTER VIEW cleaned_population AS
SELECT zip_code, SUM(zip_population) AS total_population
FROM (
    SELECT *
    FROM Population
    WHERE NOT (minimum_age = 0 AND maximum_age = 0)
) AS x
GROUP BY zip_code;
```

```SQL
SELECT l.zip_code, latitude, longitude, total_population
FROM Location l
LEFT JOIN cleaned_population AS cp
ON l.zip_code = cp.zip_code
WHERE l.zip_code IS NOT NULL AND cp.zip_code IS NOT NULL
ORDER BY total_population DESC
LIMIT 100;
```

```
+----------+-----------+-------------+------------------+
| zip_code | latitude  | longitude   | total_population |
+----------+-----------+-------------+------------------+
| 60629    | 41.775868 |  -87.711496 |           113916 |
| 79936    | 31.776593 | -106.296976 |           111086 |
| 11368    | 40.751718 |  -73.851822 |           109931 |
| 00926    | 18.345400 |  -66.051545 |           108862 |
...
...
...
```

Plotting these 100 `(latitude, longitude)` pairs gives a nice overview of where these very highly populated areas are located.

![Top 100 most populous ZIP Codes](https://i.imgur.com/ch2sHuw.png)

If I take instead the top 5000 rows and create a scatter plot from that data, I get an image that shows nicely how the Eastern part of the USA is far more densely populated than most of the rest of the country.

![Top 100 most populous ZIP Codes](https://i.imgur.com/yQN9dwB.png)

#

Now I want to do some things with the state capitals. The data inside the Capitals table is as follows
```SQL
SELECT * FROM Capitals;
```

```
+----------------+-------------+----------------+----------+
| state_long     | state_short | capital        | zip_code |
+----------------+-------------+----------------+----------+
| Alabama        | AL          | Montgomery     | 36043    |
| Alaska         | AK          | Juneau         | 99801    |
...
...
...
| Wisconsin      | WI          | Madison        | 53558    |
| Wyoming        | WY          | Cheyenne       | 82001    |
+----------------+-------------+----------------+----------+
```

There isn't much to be done with this data as it is, but one question to ask is which ZIP Code out of those that are given has the highest population? Of course having the highest population ZIP Code doesn't mean that it is the highest population capital, but I am still interested in finding out.


```SQL
SELECT state_long, state_short, capital, cp.zip_code, total_population
FROM Capitals
LEFT JOIN cleaned_population AS cp
ON Capitals.zip_code = cp.zip_code
ORDER BY total_population DESC
LIMIT 5;
```

```
+--------------+-------------+------------+----------+------------------+
| state_long   | state_short | capital    | zip_code | total_population |
+--------------+-------------+------------+----------+------------------+
| Texas        | TX          | Austin     | 78613    |            65099 |
| Oregon       | OR          | Salem      | 97301    |            53518 |
| Kentucky     | KY          | Frankfort  | 40601    |            49566 |
| California   | CA          | Sacramento | 94303    |            45467 |
| Rhode Island | RI          | Providence | 02860    |            45199 |
+--------------+-------------+------------+----------+------------------+
```

# Travelling Salesman Problem

The Travelling Salesman Problem (TSP) asks the question: "Given a list of cities and the distances between each pair of cities, what is the shortest possible route that visits each city exactly once and returns to the origin city?"

Bearing in mind that I have the `(latitude, longitude)` of each state capital and the distance between two of these pairs can be calculated, I have everything I need to get the data necessary for it to be solvable.

First, I will have to create a function that will calculate the distance between two cities given their respective `(latitude, longitude)`s.

```SQL
-- The working out of this function was done by the author of this blog;
-- I rewrote it into MySQL syntax
-- http://www.johndcook.com/blog/python_longitude_latitude/

DELIMITER $$
DROP FUNCTION IF EXISTS distance$$

CREATE FUNCTION distance (
    lat1 DECIMAL(10,6),
    long1 DECIMAL(10,6),
    lat2 DECIMAL(10,6),
    long2 DECIMAL(10,6)
)
RETURNS FLOAT
BEGIN
  DECLARE degs_to_rads, phi1, phi2, theta1, theta2, cosine, radius FLOAT;
  SET radius = 6378.388;
  SET degs_to_rads = PI() / 180;
  SET phi1 = (90.0 - lat1) * degs_to_rads;
  SET phi2 = (90.0 - lat2) * degs_to_rads;
  SET theta1 = long1 * degs_to_rads;
  SET theta2 = long2 * degs_to_rads;

  SET cosine = sin(phi1)*sin(phi2)*cos(theta1 - theta2) + cos(phi1)*cos(phi2);

  RETURN acos(cosine) * radius;
END$$
DELIMITER ;
```

With this function, my plan is to calculate the distance between every pair of ZIP Codes and export that data to python. There, I can use a library to solve for a solution and then import that data back into a new table in the database.

It should be noted that there is no guarantee that the solution found will be optimal, but it should be expected to be quite close.

I will create another view now that limits the number of states in the next queries to just 4, so that it is much easier to ensure everything is working as intended. Once I am happy that it is, I can then easily scale up to all 50 states.

```SQL
CREATE VIEW small AS
SELECT state_long, state_short, capital, c.zip_code, latitude, longitude
FROM (
    SELECT * 
    FROM Capitals 
    WHERE state_short LIKE 'A%'
) AS c
LEFT JOIN Location AS l
ON c.zip_code = l.zip_code;
```

```SQL
SELECT * FROM small;
```

```
+------------+-------------+-------------+----------+-----------+-------------+
| state_long | state_short | capital     | zip_code | latitude  | longitude   |
+------------+-------------+-------------+----------+-----------+-------------+
| Alabama    | AL          | Montgomery  | 36043    | 32.201153 |  -86.420747 |
| Alaska     | AK          | Juneau      | 99801    | 58.372910 | -134.178445 |
| Arizona    | AZ          | Phoenix     | 85003    | 33.450662 | -112.078353 |
| Arkansas   | AR          | Little Rock | 72201    | 34.746905 |  -92.280049 |
+------------+-------------+-------------+----------+-----------+-------------+
```

To get the distances between each pair of cities, I need to do a full outer join so that every state, latitude, and longitude is matched with every other state, latitude, and longitude.

```SQL
CREATE VIEW outerjoin_small AS
SELECT 
  s1.state_short AS state1, s1.latitude AS latitude1, s1.longitude AS longitude1,
  s2.state_short AS state2, s2.latitude AS latitude2, s2.longitude AS longitude2
FROM small AS s2, small AS s1;
```

```SQL
SELECT * FROM outerjoin_small;
```

```
+--------+-----------+-------------+--------+-----------+-------------+
| state1 | latitude1 | longitude1  | state2 | latitude2 | longitude2  |
+--------+-----------+-------------+--------+-----------+-------------+
| AL     | 32.201153 |  -86.420747 | AR     | 34.746905 |  -92.280049 |
| AL     | 32.201153 |  -86.420747 | AZ     | 33.450662 | -112.078353 |
| AL     | 32.201153 |  -86.420747 | AK     | 58.372910 | -134.178445 |
| AL     | 32.201153 |  -86.420747 | AL     | 32.201153 |  -86.420747 |
| AK     | 58.372910 | -134.178445 | AR     | 34.746905 |  -92.280049 |
| AK     | 58.372910 | -134.178445 | AZ     | 33.450662 | -112.078353 |
| AK     | 58.372910 | -134.178445 | AK     | 58.372910 | -134.178445 |
| AK     | 58.372910 | -134.178445 | AL     | 32.201153 |  -86.420747 |
| AZ     | 33.450662 | -112.078353 | AR     | 34.746905 |  -92.280049 |
| AZ     | 33.450662 | -112.078353 | AZ     | 33.450662 | -112.078353 |
| AZ     | 33.450662 | -112.078353 | AK     | 58.372910 | -134.178445 |
| AZ     | 33.450662 | -112.078353 | AL     | 32.201153 |  -86.420747 |
| AR     | 34.746905 |  -92.280049 | AR     | 34.746905 |  -92.280049 |
| AR     | 34.746905 |  -92.280049 | AZ     | 33.450662 | -112.078353 |
| AR     | 34.746905 |  -92.280049 | AK     | 58.372910 | -134.178445 |
| AR     | 34.746905 |  -92.280049 | AL     | 32.201153 |  -86.420747 |
+--------+-----------+-------------+--------+-----------+-------------+
```

Now I must calculate the distances between each of these pairs of coordinates.

```SQL
SELECT *, distance(latitude1, longitude1, latitude2, longitude2) AS dist
FROM outerjoin_small;
```

```
+--------+-----------+-------------+--------+-----------+-------------+---------+
| state1 | latitude1 | longitude1  | state2 | latitude2 | longitude2  | dist    |
+--------+-----------+-------------+--------+-----------+-------------+---------+
| AL     | 32.201153 |  -86.420747 | AR     | 34.746905 |  -92.280049 |  613.32 |
| AL     | 32.201153 |  -86.420747 | AZ     | 33.450662 | -112.078353 | 2398.17 |
| AL     | 32.201153 |  -86.420747 | AK     | 58.372910 | -134.178445 | 4590.06 |
| AL     | 32.201153 |  -86.420747 | AL     | 32.201153 |  -86.420747 |       0 |
| AK     | 58.372910 | -134.178445 | AR     | 34.746905 |  -92.280049 | 4040.09 |
| AK     | 58.372910 | -134.178445 | AZ     | 33.450662 | -112.078353 | 3226.88 |
| AK     | 58.372910 | -134.178445 | AK     | 58.372910 | -134.178445 |       0 |
| AK     | 58.372910 | -134.178445 | AL     | 32.201153 |  -86.420747 | 4590.06 |
| AZ     | 33.450662 | -112.078353 | AR     | 34.746905 |  -92.280049 | 1827.83 |
| AZ     | 33.450662 | -112.078353 | AZ     | 33.450662 | -112.078353 |       0 |
| AZ     | 33.450662 | -112.078353 | AK     | 58.372910 | -134.178445 | 3226.88 |
| AZ     | 33.450662 | -112.078353 | AL     | 32.201153 |  -86.420747 | 2398.17 |
| AR     | 34.746905 |  -92.280049 | AR     | 34.746905 |  -92.280049 |       0 |
| AR     | 34.746905 |  -92.280049 | AZ     | 33.450662 | -112.078353 | 1827.83 |
| AR     | 34.746905 |  -92.280049 | AK     | 58.372910 | -134.178445 | 4040.09 |
| AR     | 34.746905 |  -92.280049 | AL     | 32.201153 |  -86.420747 |  613.32 |
+--------+-----------+-------------+--------+-----------+-------------+---------+
```

This looks fairly good as there are 4 distance values of 0, which is expected for the distance between a state capital and itself. One other thing that stands out is that Alaska (AK) is very far away from the other states, which is good for a sanity check.

Feeling happy that the code is correct, I will do the last few steps again but with all states, and then export the data to python where I will solve the TSP.

```SQL
CREATE VIEW large AS
SELECT state_long, state_short, capital, c.zip_code, latitude, longitude
FROM Capitals AS c
LEFT JOIN Location AS l ON c.zip_code = l.zip_code;

CREATE VIEW outerjoin_large AS
SELECT 
  l1.state_short AS state1, l1.latitude AS latitude1, l1.longitude AS longitude1,
  l2.state_short AS state2, l2.latitude AS latitude2, l2.longitude AS longitude2
FROM large AS l2, large AS l1;

CREATE VIEW all_distances AS
SELECT *, distance(latitude1, longitude1, latitude2, longitude2) AS dist
FROM outerjoin_large;
```

After putting it through a Python TSP Solver, I found the optimal route, so I'll add add a new table to the database.

```SQL
CREATE TABLE Optimal (
    node_number INT PRIMARY KEY NOT NULL,
    state1_long VARCHAR(32),
    state1_short VARCHAR(2),
    state2_short VARCHAR(2)
);

LOAD DATA LOCAL INFILE 'C:/Users/Chris/Dev/US_ZIP/TSP_solution.csv'
INTO TABLE Optimal
FIELDS TERMINATED BY ','
LINES TERMINATED BY '\n'
IGNORE 1 ROWS
(node_number, state1_long, state1_short,state2_short);
```

Now, I can execute a join to get the corresponding distances.

```SQL
SELECT o.*, l.dist FROM Optimal AS o
LEFT JOIN all_distances AS l
ON o.state1_short = l.state1 AND o.state2_short = l.state2
```

```
+-------------+----------------+--------------+--------------+---------+
| node_number | state1_long    | state1_short | state2_short | dist    |
+-------------+----------------+--------------+--------------+---------+
|           1 | Alabama        | AL           | FL           | 285.059 |
|           2 | Florida        | FL           | SC           |  499.12 |
|           3 | South Carolina | SC           | NC           | 295.866 |
|           4 | North Carolina | NC           | VA           | 223.873 |
...
...
...
|          45 | Texas          | TX           | LA           | 636.824 |
|          46 | Louisiana      | LA           | MS           | 225.868 |
|          47 | Mississippi    | MS           | AR           | 335.634 |
|          48 | Arkansas       | AR           | TN           | 523.304 |
|          49 | Tennessee      | TN           | GA           | 345.781 |
|          50 | Georgia        | GA           | AL           | 256.548 |
+-------------+----------------+--------------+--------------+---------+
```
And finally, sum these distances for a grand total.

```SQL
SELECT ROUND(SUM(dist)) AS total_distance_km
FROM (
    SELECT o.*, l.dist FROM Optimal AS o
    LEFT JOIN all_distances AS l
    ON o.state1_short = l.state1 AND o.state2_short = l.state2
) AS x;
```

```
+-------------------+
| total_distance_km |
+-------------------+
|             26569 |
+-------------------+
```

So there it is, the shortest route I found that travels through every state capital and returns to the original one is 26,569 km long.
