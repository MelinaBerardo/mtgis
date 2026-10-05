from .mtConstants import *
from .mtOffset import *
from .mtQAQC import *
from .mtFuncs import *
from .mtSegments import *
from .mtAssemblies import defineAssembly
from .mtTree import mtTree
from .mtSplices import generateSplices
from .mtAttenuacion import atenuacionAll
from .mtCableTraces import mtCableTraces
from .mtHerrajes import crearHerrajes, createHerrajeRienda
from .mtLayerRelations import *
from .mtSld import *
import processing
from anytree import RenderTree
from .mtCallTimer import mtCallTimer
from .mtMissingFields import updateProjectTables

def checkUFS():
    thisDict=({
    'Chequeo_3' :{
    'desc':'chequea que todas las UF esten contenidas',
    'test': CheckUFContenidas,
    'order':30000,
    },})

    linkUFtoArea()
    QAQC_Table(thisDict,True)


def runQAQC():
    QAQC_Table(QAQC_DICT,True)
    
def runUnificadoQAQC():
    QAQC_Table(QAQC_DICT_UNIFICADO,True)

def runPredisenoQAQC():
    QAQC_Table(QAQC_DICT_PREDISENO,True)

def runPostesQAQC():
    QAQC_Table(QAQC_DICT_POSTES,True)

def runCajasQAQC():
    QAQC_Table(QAQC_DICT_CAJAS,True)
    
    
    


def runTasaProject():

    myTree = mtTree()   
    myTree.buildTree()
    netTASAProject(myTree)        
    assignProjectToSuspensor()
    infraTasaProject()
    defineAssembly(layerNode)
    defineAssembly(layerCable)
    defineAssembly(layerHerrajes)
    defineAssembly(layerInfra)
    defineAssembly(layerSuspensor)
    ajustarCampos()


def buildSld(skipHub=False):
    myTree = mtTree()
    myTree.buildTree()
    mySegments = mtSegments()
    mySegments.clear()
    mySegments.loadFromTable(layerSEG)
    out=getFullGraph(myTree,mySegments, skipHubs=skipHub)
    print(out)

def Segmentar():
    myTree = mtTree()
    mySegments = mtSegments()
    mySegments.clear()
    segmentCable(myTree,layerCable,layerSEG)
    processing.run(OFFSET_CABLE_MODEL,{'offsetmultiplier':2,'startoffset':1.5})  #este va siempre al final

def testOffset():
    myTree = mtTree()
    mySegments = mtSegments()
    updateAllOffsets()
    mySegments.clear()
    segmentCable(myTree,layerCable,layerSEG)
    mySegments.loadFromTable(layerSEG)
    processing.run(OFFSET_CABLE_MODEL,{'offsetmultiplier':2,'startoffset':1.5})  #este va siempre al final

def nomencladoNumerado(): #importante el orden de estas funciones!
    relationsNode_Area.updateRelations()
    relationsNode_Cable.updateRelations()
    relationsNode_Infra.updateRelations()
    relationsNode_Manzana.updateRelations()
    relationsNode_Vereda.updateRelations()
    relationsInfra_Suspensor.updateRelations()
    linkFeatures()

    myTree = mtTree()
    myTree.buildTree()
    # segmentCable(myTree,layerCable,layerSEG)
    
    mySegments = mtSegments()
    mySegments.clear()
    mySegments.loadFromTable(layerSEG)
    #numberAccAlim(myTree, updateNames=True)
    numberDistribucion(myTree)
    nameDistribucion(myTree)


def setAssemblies():
    defineAssembly(layerNode)
    defineAssembly(layerCable)
    defineAssembly(layerHerrajes)
    defineAssembly(layerInfra)
    defineAssembly(layerSuspensor)
    ajustarCampos()

def splices():
    relationsNode_Cable.updateRelations()
    myTree = mtTree()
    mySegments = mtSegments()
    mySegments.loadFromTable(layerSEG)
    #print(RenderTree(myTree.buildTree()))
   # print(myTree.getNodesAsList(tipoFilter=geomType.NODE, tipoNodoFilter=elementType.HUB))
    generateSplices(myTree, mySegments, True)
    
    




def onlyLink():
    if checkErrorsNetwork():
        timer=mtCallTimer('onlyLink')
        timer2=mtCallTimer('onlyLinkFull')
        timer.print_lap("start onlyLink")
        timer2.print_lap("start onlyLinkFull")
        relationsNode_Area.updateRelations()
        timer.print_lap("updateRelations node_Area")
        relationsNode_Cable.updateRelations()
        timer.print_lap("updateRelations relationsNode_Cable")
        relationsNode_Infra.updateRelations()
        timer.print_lap("updateRelations relationsNode_Infra")
        relationsNode_Manzana.updateRelations()
        timer.print_lap("updateRelations relationsNode_Manzana")
        relationsNode_Vereda.updateRelations()
        timer.print_lap("updateRelations relationsNode_Vereda")
        relationsInfra_Suspensor.updateRelations()
        timer.print_lap("updateRelations relationsInfra_Suspensor")

        applyDefaultFieldValues(layerNode)
        timer.print_lap("applyDefaultFieldValues layerNode")
        applyDefaultFieldValues(layerCable)
        timer.print_lap("applyDefaultFieldValues layerCable")
        applyDefaultFieldValues(layerHerrajes)
        timer.print_lap("applyDefaultFieldValues layerHerrajes")

        linkFeatures()
        timer.print_lap("end linkFeatures")
        timer2.print_lap("end onlyLink")
        

def onlyLinkNoResetComputedFields():
    relationsNode_Area.updateRelations()
    relationsNode_Cable.updateRelations()
    relationsNode_Infra .updateRelations()

    applyDefaultFieldValues(layerNode)
    applyDefaultFieldValues(layerCable)
    applyDefaultFieldValues(layerHerrajes)

    processing.run('project:removeDuplicateNodes',{'layertoremoveduplicates':layerCable.LID})

    linkFeatures()
    
    print("listo el Pollo!")
    
def createHerrajes():
    createInfraNodesSuspensores()
    myTree = mtTree()
    myTree.buildTree()
    myTraces=mtCableTraces()
    myTraces.updateTable()
    myTraces.loadAllFromTable()
    assignProjectToSuspensor()
    crearHerrajes(myTraces,myTree)
    infraTasaProject()
    

            
def runNetworkTimeTest():
    if checkErrorsNetwork():
        timer=mtCallTimer('onlyLink')
        relationsNode_Area.updateRelations()
        relationsNode_Cable.updateRelations()
        relationsNode_Infra.updateRelations()
        relationsNode_Manzana.updateRelations()
        relationsNode_Vereda.updateRelations()
        relationsInfra_Suspensor.updateRelations()
        timer.print_lap("updateRelations")

        applyDefaultFieldValues(layerNode)
        applyDefaultFieldValues(layerCable)
        applyDefaultFieldValues(layerHerrajes)
        timer.print_lap("applyDefaultFieldValues")

        linkFeatures()
        timer.print_lap("linkFeatures")
        setDistanceAlong(layerNode)
        timer.print_lap("setDistanceAlong") 
        myTree = mtTree()   
        setCompleteDistanceAlong(myTree)
        timer.print_lap("setCompleteDistanceAlong")
        setEndPoint(myTree)
        timer.print_lap("setEndPoint")
        demandAggregation(myTree)
        timer.print_lap("demandAggregation")
        calculateFibers(layerCable)
        timer.print_lap("calculateFibers")
        mySegments = mtSegments()
        updateAllOffsets()
        timer.print_lap("updateAllOffsets")
        mySegments.clear()
        segmentCable(myTree,layerCable,layerSEG)
        timer.print_lap("segmentCable")
        mySegments.loadFromTable(layerSEG)
        timer.print_lap("mySegments.loadFromTable")
        myTraces=mtCableTraces()
        myTraces.updateTable()
        timer.print_lap("myTraces.updateTable()")
        myTraces.loadAllFromTable()
        timer.print_lap("myTraces.loadAllFromTable")
        netTASAProject(myTree)
        createInfraNodesSuspensores()
        crearHerrajes(myTraces,myTree)
        timer.print_lap("crearHerrajes")
        updateJumperCableFields()
        timer.print_lap("updateJumperCableFields")
        numberAccAlim(myTree, updateNames=True)
        timer.print_lap("numberAccAlim")
        numberDistribucion(myTree)
        timer.print_lap("numberDistribucion")
        nameDistribucion(myTree)
        timer.print_lap("nameDistribucion")
        defineAssembly(layerNode)
        timer.print_lap("defineAssembly(layerNode)")
        defineAssembly(layerCable)
        timer.print_lap("defineAssembly(layerCable)")
        defineAssembly(layerHerrajes)
        timer.print_lap("defineAssembly(layerHerrajes)")
        generateSplices(myTree, mySegments, True)
        timer.print_lap("generateSplices")
        processing.run(OFFSET_CABLE_MODEL,{ 'offsetmultiplier' : 1, 'startoffset' : 1.0,'truncate':True, 'zoomlevel' : 1 })
        timer.print_lap("processing.run(OFFSET_CABLE_MODEL")
        ajustarCampos()
        timer.print_lap("ajustarCampos")





def runNetwork():

    updateProjectTables()
    if checkAtributosG() and checkErrorsNetwork():
        relationsNode_Area.updateRelations()
        relationsNode_Cable.updateRelations()
        relationsNode_Infra.updateRelations()
        relationsNode_Manzana.updateRelations()
        relationsNode_Vereda.updateRelations()
        relationsInfra_Suspensor.updateRelations()

        applyDefaultFieldValues(layerNode)
        applyDefaultFieldValues(layerCable)
        applyDefaultFieldValues(layerHerrajes)
        createInfraNodes()
        linkFeatures()
        setDistanceAlong(layerNode)
        myTree = mtTree()   
        myTree.buildTree()
        setCompleteDistanceAlong(myTree)
        setEndPoint(myTree)
        demandAggregation(myTree)
        calculateFibers(layerCable)
        myTraces=mtCableTraces()
        myTraces.updateTable()
        myTraces.loadAllFromTable()
        numberAccAlim(myTree, updateNames=True)
        processing.run(CHIRALITY,{})
        linkNetParents(myTree)
        numberDistribucion(myTree)
        nameDistribucion(myTree)    
        groupSplices(myTree)     
        mySegments = mtSegments()        
        mySegments.clear()
        segmentCable(myTree,layerCable,layerSEG)
        mySegments.loadFromTable(layerSEG)        
        updateAllOffsets()
       
        crearHerrajes(myTraces,myTree)
        categorizeCableTraces()
        camarasEnUso()
        updateJumperCableFields()

        defineAssembly(layerNode)
        defineAssembly(layerCable)
        defineAssembly(layerHerrajes)
        defineAssembly(layerInfra)
        defineAssembly(layerSuspensor)
        generateSplices(myTree, mySegments, True)
    
        processing.run(OFFSET_CABLE_MODEL,{ 'offsetmultiplier' : 1, 'startoffset' : 1.0,'truncate':True, 'zoomlevel' : 1 })
        ajustarCampos()




def runEntregables():

    relationsNode_Cable.updateRelations()    
    myTree = mtTree()   
    myTree.buildTree()
    myTraces=mtCableTraces()
    myTraces.updateTable()
    myTraces.loadAllFromTable()  
    RedAccesoTasaProject()
    groupSplices(myTree)     
    netTASAProject(myTree) 
    manzanaIntersectTasa()    
    mySegments = mtSegments()        
    mySegments.clear()
    segmentCable(myTree,layerCable,layerSEG)
    mySegments.loadFromTable(layerSEG)      
    assignProjectToSuspensor()
    crearHerrajes(myTraces,myTree)
    updateJumperCableFields()
    infraTasaProject()

    defineAssembly(layerNode)
    defineAssembly(layerCable)
    defineAssembly(layerHerrajes)
    defineAssembly(layerInfra)
    defineAssembly(layerSuspensor)
    processing.run(CREAR_COTAS,{})   
    generateSplices(myTree, mySegments, True)     
    processing.run(OFFSET_CABLE_MODEL,{ 'offsetmultiplier' : 1, 'startoffset' : 1.0,'truncate':True, 'zoomlevel' : 1 })
    updateAreasFibers()
    ajustarCampos()
        
        
        
        

def testJSM():


    # relationsNode_Cable.updateRelations()
    myTree = mtTree()  
    print(RenderTree(myTree.buildTree()))
    groupSplices(myTree) 
    mySegments = mtSegments()
    mySegments.loadFromTable(layerSEG)
    #print(RenderTree(myTree.buildTree()))
    # print(myTree.getNodesAsList(tipoFilter=geomType.NODE, tipoNodoFilter=elementType.HUB))
    generateSplices(myTree, mySegments, True)
               
           
def testNico():
    
    relationsNode_Area.updateRelations()
    relationsNode_Cable.updateRelations()
    relationsNode_Infra.updateRelations()
 
    applyDefaultFieldValues(layerNode)
    applyDefaultFieldValues(layerCable)
    applyDefaultFieldValues(layerHerrajes)
 
    #linkFeatures()
    setDistanceAlong(layerNode)
    createInfraNodes()
    myTree = mtTree()  
    setCompleteDistanceAlong(myTree)
    myTree = mtTree()
    mySegments = mtSegments()
    #updateAllOffsets()
    mySegments.clear()
    segmentCable(myTree,layerCable,layerSEG)    
    mySegments.loadFromTable(layerSEG)
    myTraces=mtCableTraces()
    myTraces.updateTable()
    myTraces.loadAllFromTable()
    #netTASAProject(myTree)        
    #assignProjectToSuspensor()
    crearHerrajes(myTraces,myTree)
    updateJumperCableFields()
    #infraTasaProject()
 
    updateJumperCableFields()
    # print(RenderTree(myTree.buildTree()))
    
    
    
