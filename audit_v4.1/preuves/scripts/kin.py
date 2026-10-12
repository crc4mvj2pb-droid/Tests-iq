import sys, math; sys.path.insert(0, sys.argv[1])
from chemical_kinetics import simulate_reaction_network as sim, ChemicalKineticsError
def run(species, reactions, T=10, dt=0.01, **kw):
    return sim({"species":species,"reactions":reactions,"duration":T,"dt":dt,**kw})
# 1st order A->B k=0.3
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":0.3}])
A=d["summary"]["final_concentrations"]["A"]; print("1st order  A(10)=",A," exact",math.exp(-3)," relerr",abs(A-math.exp(-3))/math.exp(-3))
# 2nd order 2A->P k=0.5 : dA/dt=-2k A^2 -> A=1/(1/A0+2kt)
d=run([{"id":"A","initial_concentration":1},{"id":"P","initial_concentration":0}],[{"id":"r","reactants":{"A":2},"products":{"P":1},"rate_constant":0.5}])
A=d["summary"]["final_concentrations"]["A"]; ex=1/(1+2*0.5*10); print("2nd order  A(10)=",A," exact",ex," relerr",abs(A-ex)/ex)
# A->B->C k1=1,k2=0.5 : B=k1/(k2-k1)(e^-k1t - e^-k2t)
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0},{"id":"C","initial_concentration":0}],[{"id":"r1","reactants":{"A":1},"products":{"B":1},"rate_constant":1},{"id":"r2","reactants":{"B":1},"products":{"C":1},"rate_constant":0.5}],T=4)
B=d["summary"]["final_concentrations"]["B"]; ex=1/(0.5-1)*(math.exp(-4)-math.exp(-2)); print("A->B->C    B(4)=",B," exact",ex," relerr",abs(B-ex)/ex)
# Arrhenius: Ea=50kJ, T=308.15 vs Tref 298.15 -> factor
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":0.1,"activation_energy_j_mol":50000}],temperature_k=308.15)
kT=0.1*math.exp(-50000/8.314462618*(1/308.15-1/298.15)); A=d["summary"]["final_concentrations"]["A"]; print("Arrhenius  A(10)=",A," exact",math.exp(-kT*10))
# reversible A<->B equilibrium K=kf/kr=2
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"f","reactants":{"A":1},"products":{"B":1},"rate_constant":2},{"id":"b","reactants":{"B":1},"products":{"A":1},"rate_constant":1}],T=20)
f=d["summary"]["final_concentrations"]; print("reversible B/A=",f["B"]/f["A"],"(expect 2)")
# edge: duplicate reaction ids
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":0.1},{"id":"r","reactants":{"B":1},"products":{"A":1},"rate_constant":5}])
print("duplicate reaction ids accepted; final_rates keys:",list(d["summary"]["final_rates"]))
# edge: stiff k with large dt
try: run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":100}],dt=0.1); print("stiff: accepted")
except ChemicalKineticsError as e: print("stiff dt=0.1 k=100 ->",e)
# edge: moderately stiff, k*dt=2.5 (RK4 stability limit ~2.785): no negative but oscillation?
d=run([{"id":"A","initial_concentration":1},{"id":"B","initial_concentration":0}],[{"id":"r","reactants":{"A":1},"products":{"B":1},"rate_constant":25}],dt=0.1,T=1)
print("k*dt=2.5: A(1)=",d["summary"]["final_concentrations"]["A"],"exact",math.exp(-25),"(no accuracy warning emitted:", 'warning' not in str(d).lower(),")")
# atom balance: unbalanced
d=run([{"id":"H2","initial_concentration":1,"atoms":{"H":2}},{"id":"O2","initial_concentration":1,"atoms":{"O":2}},{"id":"H2O","initial_concentration":0,"atoms":{"H":2,"O":1}}],[{"id":"r","reactants":{"H2":1,"O2":1},"products":{"H2O":1},"rate_constant":0.1}])
print("unbalanced H2+O2->H2O atom balance:",d["summary"]["atom_balance_by_reaction"],"-> simulation still returned (status):",d.get("model_id"))
