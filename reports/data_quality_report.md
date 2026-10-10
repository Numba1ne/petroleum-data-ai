# Volve Production Data Quality Report

## Key Findings

Raw daily data shape: (15634, 24)
Date range: 2007-09-01 00:00:00 to 2016-12-01 00:00:00
Unique wells: 7
Raw monthly data shape: (527, 10)

Missing values before handling:
on_stream_hrs                285
avg_downhole_pressure       6654
avg_downhole_temperature    6654
avg_dp_tubing               6654
avg_annulus_press           7744
avg_choke_size_p            6715
avg_choke_uom               6473
avg_whp_p                   6479
avg_wht_p                   6488
dp_choke_size                294
bore_oil_vol                6473
bore_gas_vol                6473
bore_wat_vol                6473
bore_wi_vol                 9928
water_cut                   7624
gor                         6473
onstream_efficiency          285
dtype: int64

Missing values after handling:
on_stream_hrs                285
avg_downhole_pressure       6642
avg_downhole_temperature    6642
avg_dp_tubing               6654
avg_annulus_press           7744
avg_choke_size_p            6715
avg_choke_uom               6473
avg_whp_p                   6479
avg_wht_p                   6488
dp_choke_size                278
bore_oil_vol                6473
bore_gas_vol                6473
bore_wat_vol                6473
bore_wi_vol                 9928
water_cut                   7624
gor                         6473
onstream_efficiency          285
dtype: int64

Summary statistics for cleaned daily data:
                             dateprd  npd_well_bore_code  npd_field_code  npd_facility_code  on_stream_hrs  avg_downhole_pressure  avg_downhole_temperature  avg_dp_tubing  avg_annulus_press  avg_choke_size_p    avg_whp_p    avg_wht_p  dp_choke_size  bore_oil_vol   bore_gas_vol  bore_wat_vol   bore_wi_vol    water_cut          gor  onstream_efficiency
count                          15634        15634.000000         15634.0            15634.0   15349.000000            8992.000000               8992.000000    8980.000000        7890.000000       8919.000000  9155.000000  9146.000000   15356.000000   9161.000000    9161.000000   9161.000000   5706.000000  8010.000000  9161.000000         15349.000000
mean   2012-11-07 17:39:58.004349440         5908.581745       3420717.0           369304.0      19.994093             181.700206                 77.117101     154.028787          14.856100         55.168533    45.377811    67.728440      11.436879   1095.631548  161049.059703   1672.151332   5315.480815     0.535257   132.834846             0.833087
min              2007-09-01 00:00:00         5351.000000       3420717.0           369304.0       0.000000               0.000000                  0.000000       0.000000           0.000000          0.000000     0.000000     0.000000       0.000000      0.000000       0.000000   -457.840000      0.000000    -2.614436     0.000000             0.000000
25%              2010-07-30 00:00:00         5599.000000       3420717.0           369304.0      24.000000               0.000000                  0.000000      83.665361          10.841437         18.952989    31.148062    56.577834       0.000000    190.690000   29430.590000     19.870000   4338.204674     0.158802   142.768362             1.000000
50%              2013-05-08 00:00:00         5693.000000       3420717.0           369304.0      24.000000             232.798676                103.176161     175.588861          16.308598         52.096877    37.933620    80.071250       2.379874    557.550000   87749.660000   1097.790000   5504.739769     0.637998   149.957665             1.000000
75%              2015-02-19 00:00:00         5769.000000       3420717.0           369304.0      24.000000             255.382274                106.276063     204.319964          21.306125         99.924288    57.101268    88.062202      13.763126   1345.200000  202482.300000   3260.950000   6781.058040     0.849616   155.896034             1.000000
max              2016-12-01 00:00:00         7405.000000       3420717.0           369304.0      25.000000             397.588550                108.502178     345.906770          30.019828        100.000000   137.311030    93.509584     125.718570   5901.840000  851131.520000   8019.740000  10013.600000     1.000000  1110.185309             1.041667
std                              NaN          649.231622             0.0                0.0       8.369978             109.754403                 45.677954      76.752373           8.406822         36.692924    24.752631    27.719028      19.817783   1323.538151  188136.410434   1706.982853   2181.486695     0.345245    52.700818             0.348749