Demo Classical PSHA for Vancouver Schools
=========================================

============== ===================
checksum32     2,897,711,382      
date           2018-04-14T06:36:11
engine_version 3.1.0-git32e4371   
============== ===================

num_sites = 3, num_levels = 36

Parameters
----------
=============================== ==================
calculation_mode                'classical'       
number_of_logic_tree_samples    0                 
maximum_distance                {'default': 400.0}
investigation_time              1.0               
ses_per_logic_tree_path         1                 
truncation_level                3.0               
rupture_mesh_spacing            5.0               
complex_fault_mesh_spacing      5.0               
width_of_mfd_bin                0.1               
area_source_discretization      50.0              
ground_motion_correlation_model None              
minimum_intensity               {}                
random_seed                     23                
master_seed                     0                 
ses_seed                        42                
=============================== ==================

Input files
-----------
======================= ============================================================
Name                    File                                                        
======================= ============================================================
gsim_logic_tree         `nbc_asc_logic_tree.xml <nbc_asc_logic_tree.xml>`_          
job_ini                 `job.ini <job.ini>`_                                        
sites                   `vancouver_school_sites.csv <vancouver_school_sites.csv>`_  
source                  `vancouver_area_source.xml <vancouver_area_source.xml>`_    
source_model_logic_tree `source_model_logic_tree.xml <source_model_logic_tree.xml>`_
======================= ============================================================

Composite source model
----------------------
========= ====== =============== ================
smlt_path weight gsim_logic_tree num_realizations
========= ====== =============== ================
b1        1.000  simple(3)       3/3             
========= ====== =============== ================

Required parameters per tectonic region type
--------------------------------------------
====== ========================================================================================================================================== ========= ========== ==========
grp_id gsims                                                                                                                                      distances siteparams ruptparams
====== ========================================================================================================================================== ========= ========== ==========
0      GMPETable(gmpe_table='Wcrust_high_rhypo.hdf5') GMPETable(gmpe_table='Wcrust_low_rhypo.hdf5') GMPETable(gmpe_table='Wcrust_med_rhypo.hdf5') rhypo                mag       
====== ========================================================================================================================================== ========= ========== ==========

Realizations per (TRT, GSIM)
----------------------------

::

  <RlzsAssoc(size=3, rlzs=3)
  0,GMPETable(gmpe_table='Wcrust_high_rhypo.hdf5'): [2]
  0,GMPETable(gmpe_table='Wcrust_low_rhypo.hdf5'): [0]
  0,GMPETable(gmpe_table='Wcrust_med_rhypo.hdf5'): [1]>

Number of ruptures per tectonic region type
-------------------------------------------
========================= ====== ==================== ============ ============
source_model              grp_id trt                  eff_ruptures tot_ruptures
========================= ====== ==================== ============ ============
vancouver_area_source.xml 0      Active Shallow Crust 1,710        2,430       
========================= ====== ==================== ============ ============

Slowest sources
---------------
========= ============ ============ ========= ========== ========= ========= ======
source_id source_class num_ruptures calc_time split_time num_sites num_split events
========= ============ ============ ========= ========== ========= ========= ======
VICM      AreaSource   2,430        0.009     0.009      90        30        0     
========= ============ ============ ========= ========== ========= ========= ======

Computation times by source typology
------------------------------------
============ ========= ======
source_class calc_time counts
============ ========= ======
AreaSource   0.009     1     
============ ========= ======

Duplicated sources
------------------
There are no duplicated sources

Information about the tasks
---------------------------
================== ===== ========= ===== ===== =========
operation-duration mean  stddev    min   max   num_tasks
count_ruptures     0.003 7.729E-04 0.002 0.005 8        
================== ===== ========= ===== ===== =========

Informational data
------------------
============== ============================================================================= ========
task           sent                                                                          received
count_ruptures gsims=1.23 MB sources=14.87 KB param=6.8 KB srcfilter=6.44 KB monitor=2.57 KB 2.82 KB 
============== ============================================================================= ========

Slowest operations
------------------
============================== ========= ========= ======
operation                      time_sec  memory_mb counts
============================== ========= ========= ======
reading composite source model 0.033     0.0       1     
total count_ruptures           0.025     2.238     8     
managing sources               0.010     0.0       1     
splitting sources              0.010     0.016     1     
store source_info              0.006     0.0       1     
reading site collection        5.324E-04 0.0       1     
unpickling count_ruptures      3.965E-04 0.0       8     
aggregate curves               1.776E-04 0.0       8     
saving probability maps        4.387E-05 0.0       1     
============================== ========= ========= ======