# Cars Analysis 
#### Originally [PurchaseAnalysis](https://github.com/beyarkay/PurchaseAnalysis)


Cars Analysis is a collection of web-scrapers 
(`autotraders.py`, `cars.py`, `gumtree.py` and `surf4cars.py`, ) 
designed to capture information about the 
South African second hand cars market (with focus on the Western Cape), 
as well as exploratory scripts that look into price prediction (`ml.py`) or just exploratory
data analysis of the collected data (`eda.py`). 

Currently data is collected about 
23 663 second hand cars for sale in the Western Cape.

## Graphs
All extreme datapoints were omitted, to aid in the analysis 
of the majority of the cars, and to ignore possible mistakes made
when the car was put up on sale.
### Price vs Kilometers travelled, by make and year
This one is fascinating. Most makes have the expected negative relationship,
except for the luxury cars like _Porsche_:
![](price-kms(year-make).png)

However, just looking at the luxury makes, it's pretty clear that they
also heavily depreciate in value as they age, it's just that they're in
a whole different ballgame in terms of price:
![](price-kms(year-make)ZAR>=1000000.png)


You can also see the heavy duty/4x4/off-road cars _really_ lose their value 
once they're a few years old, probably because potential buyers are wary
of the heavy use they could have been put through:
![](price-kms(year-make)heavy_duty.png)


### Price vs Kilometers travelled, by _model_ and year
Looking a bit closer, we can examine how individual models from the
same manufacturer depreciate over time:
#### BMW
![](per_make/bmw-price-kms(year-model).png)
#### Ford
![](per_make/ford-price-kms(year-model).png)
#### Toyota
![](per_make/toyota-price-kms(year-model).png)
#### Volkswagen
![](per_make/volkswagen-price-kms(year-model).png)


## Data summaries
```

>>> df.info()
<class 'pandas.core.frame.DataFrame'>
RangeIndex: 23663 entries, 0 to 23662
Data columns (total 18 columns):
 #   Column        Non-Null Count  Dtype         
---  ------        --------------  -----         
 0   date_updated  23663 non-null  datetime64[ns]
 1   fuel_type     20063 non-null  category      
 2   kms           23461 non-null  float64       
 3   link          23663 non-null  object        
 4   make          23609 non-null  category      
 5   mmv_string    23578 non-null  object        
 6   model         23605 non-null  category      
 7   price         23603 non-null  float64       
 8   title         23614 non-null  object        
 9   transmission  23556 non-null  category      
 10  uid           23663 non-null  int64         
 11  variant       9451 non-null   category      
 12  website       23663 non-null  category      
 13  year          23566 non-null  float64       
 14  color         14085 non-null  category      
 15  province      23663 non-null  category      
 16  kms_per_year  23459 non-null  float64       
 17  zar_100km     23450 non-null  float64       
dtypes: category(8), datetime64[ns](1), float64(5), int64(1), object(3)
memory usage: 2.1+ MB


>>> df.describe(include='all') # Some columns omitted for brevity
       fuel_type           kms        make  model         price  \
count      20063  2.346100e+04       23609  23605  2.360300e+04  \
unique         6           NaN          76    727           NaN  \
top       petrol           NaN  volkswagen   polo           NaN  \
freq       14530           NaN        4232   1385           NaN  \
first        NaN           NaN         NaN    NaN           NaN  \
last         NaN           NaN         NaN    NaN           NaN  \
mean         NaN  7.012052e+04         NaN    NaN  2.859403e+05  \
std          NaN  7.052589e+04         NaN    NaN  3.039697e+05  \
min          NaN  0.000000e+00         NaN    NaN  1.300000e+01  \
25%          NaN  1.774500e+04         NaN    NaN  1.439000e+05  \
50%          NaN  5.262400e+04         NaN    NaN  2.040000e+05  \
75%          NaN  1.070000e+05         NaN    NaN  3.394950e+05  \
max          NaN  2.430000e+06         NaN    NaN  8.999999e+06  \

       transmission                year  color   kms_per_year     zar_100km
count         23556    945123566.000000  14085   23459.000000  2.345000e+04
unique            4     676         NaN    626            NaN           NaN
top          manual     1.6         NaN  white            NaN           NaN
freq          13468     567         NaN   5406            NaN           NaN
first           NaN     NaN         NaN    NaN            NaN           NaN
last            NaN     NaN         NaN    NaN            NaN           NaN
mean            NaN     NaN 2015.576424    NaN   11928.153916  1.422336e+08
std             NaN     NaN    4.874987    NaN    7612.631511  1.455108e+08
min             NaN     NaN 1934.000000    NaN       0.000000  0.000000e+00
25%             NaN     NaN 2014.000000    NaN    7087.533333  4.285221e+07
50%             NaN     NaN 2017.000000    NaN   11750.000000  1.055120e+08
75%             NaN     NaN 2019.000000    NaN   16000.000000  1.992581e+08
max             NaN     NaN 2020.000000    NaN  203000.000000  4.223122e+09

>>> df.quantile([0.01, 0.05, 0.10, 0.5, 0.90, 0.95, 0.99])
           kms      price     year    kms / year  zar * 100km
0.01      36.0    36000.0   1999.0     20.000000      69950.0
0.05    1000.0    79900.0   2007.0    788.000000    2899000.0
0.10    3500.0    99995.0   2010.0   2500.800000   10499300.0
0.50   52624.0   204000.0   2017.0  11750.000000  105512000.0
0.90  158000.0   514976.0   2020.0  20166.666667  318482000.0
0.95  193000.0   699900.0   2020.0  23333.333333  405081487.5
0.99  260000.0  1399900.0   2020.0  32035.364000  588393000.0

```