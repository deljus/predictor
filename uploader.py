import os
import subprocess as sp


standardize = '/home/stsouko/.ChemAxon/JChem/bin/standardize'
standardize_config_1 = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'models', 'standardize_1.xml')
standardize_config_2 = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'models', 'standardize_2.xml')

proc = sp.check_output([standardize, '-c', standardize_config_1, '-f', 'sdf', '-o', 'o.sdf'])
