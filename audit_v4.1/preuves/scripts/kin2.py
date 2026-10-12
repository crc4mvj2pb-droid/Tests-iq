import sys, math; sys.path.insert(0, sys.argv[1])
from chemical_kinetics import simulate_reaction_network as sim
d=sim({"species":[{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],"reactions":[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":15}],"duration":1,"dt":0.1})
A=d["summary"]["final_concentrations"]["A"]; print("k*dt=1.5: A(1)=%.3e exact=%.3e  ratio=%.0fx ; any accuracy warning? %s"%(A,math.exp(-15),A/math.exp(-15),[k for k in d if 'warn' in k or 'error_est' in k]))
d=sim({"species":[{"id":"H2","initial_concentration":1,"atoms":{"H":2}},{"id":"O2","initial_concentration":1,"atoms":{"O":2}},{"id":"H2O","initial_concentration":0,"atoms":{"H":2,"O":1}}],"reactions":[{"id":"r","reactants":{"H2":1,"O2":1},"products":{"H2O":1},"rate_constant":0.1}],"duration":10,"dt":0.1})
print("unbalanced H2+O2->H2O: atom_balance",d["summary"]["atom_balance_by_reaction"],"; result still returned with validation_level",d["validation_level"])
