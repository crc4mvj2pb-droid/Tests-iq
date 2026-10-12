import sys; sys.path.insert(0, sys.argv[1])
from reaction_stoichiometry import calculate_stoichiometry as cs, StoichiometryError as E
def t(name, req):
    try: d=cs(req); print(name,"->",{k:d[k] for k in d if k in("limiting_reactants","limiting_reactant","reaction_extent_mol","product_amounts_mol","remaining_reactant_amounts_mol","product_amounts_final_mol","reactant_amounts_final_mol")} or list(d)[:12])
    except E as e: print(name,"-> ERROR:",e)
sp=lambda **kw:[{"id":k,"amount_mol":v[0],"formula":v[1]} for k,v in kw.items()]
t("2H2+O2->2H2O (4 mol H2,1 mol O2)",{"reactants":{"H2":2,"O2":1},"products":{"H2O":2},"species":sp(H2=(4,"H2"),O2=(1,"O2"),H2O=(0,"H2O"))})
t("unbalanced H2+O2->H2O",{"reactants":{"H2":1,"O2":1},"products":{"H2O":1},"species":sp(H2=(4,"H2"),O2=(1,"O2"),H2O=(0,"H2O"))})
t("fake element Xy",{"reactants":{"A":1},"products":{"B":1},"species":sp(A=(1,"Xy"),B=(0,"Xy"))})
t("Ca(OH)2+2HCl->CaCl2+2H2O",{"reactants":{"C":1,"HCl":2},"products":{"CaCl2":1,"W":2},"species":sp(C=(1,"Ca(OH)2"),HCl=(1,"HCl"),CaCl2=(0,"CaCl2"),W=(0,"H2O"))})
t("formula missing",{"reactants":{"A":1},"products":{"B":1},"species":[{"id":"A","amount_mol":1},{"id":"B","amount_mol":0}]})
