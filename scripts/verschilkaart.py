import os
import glob
import geopandas as gpd
import pandas as pd
import sys
import zipfile
import shutil
import fiona

job_id = sys.argv[1]

scriptDirectory = os.path.dirname(os.path.abspath(__file__))
basePath = os.path.abspath(os.path.join(scriptDirectory, '..'))

def prepareInputdata(basePath, job_id):
    uitsnedePathZip = os.path.join(basePath, 'data', 'temp', str(job_id)) + '_u.zip'
    mutatiePathZip = os.path.join(basePath, 'data', 'temp', str(job_id)) + '_m.zip'
    if not os.path.exists(uitsnedePathZip):
        print("(Error) Geüploadde uitsnede file is geen .zip bestand")
        deleteUploads(basePath)
        return
    if not os.path.exists(mutatiePathZip):
        print("(Error) Geüploadde mutatie file is geen .zip bestand")
        deleteUploads(basePath)
        return
    uitsnedeUnzipPath = os.path.join(basePath, 'data', 'temp', str(job_id) + '_u')
    mutatieUnzipPath = os.path.join(basePath, 'data', 'temp', str(job_id) + '_m')
    if not os.path.exists(uitsnedeUnzipPath):
        os.makedirs(uitsnedeUnzipPath)
    if not os.path.exists(mutatieUnzipPath):
        os.makedirs(mutatieUnzipPath)

    with zipfile.ZipFile(uitsnedePathZip, 'r') as zip_ref:
        zip_ref.extractall(uitsnedeUnzipPath)
    with zipfile.ZipFile(mutatiePathZip, 'r') as zip_ref:
        zip_ref.extractall(mutatieUnzipPath)
    checkInput(uitsnedeUnzipPath, mutatieUnzipPath)

def checkInput(uitsnedePath, mutatiePath):
    gdbcheckU = glob.glob(os.path.join(uitsnedePath, "*.gdb"))
    gdbcheckM = glob.glob(os.path.join(mutatiePath, "*.gdb"))
    shpcheckU = glob.glob(os.path.join(uitsnedePath, "*.shp"))
    shpcheckM = glob.glob(os.path.join(mutatiePath, "*.shp"))
    gdbCondition = False
    shpCondition = False
    #Check if each folder has 1 .gdb file
    if len(gdbcheckU) == 1 and len(gdbcheckM) == 1:
        gdbCondition = True
        gdbPathUitsnede = gdbcheckU[0]
        gdbPathMutatie = gdbcheckM[0]
        listGdbfiles(gdbPathUitsnede, gdbPathMutatie)
    #Check if each folder has 1 or more .shp files
    if len(shpcheckU) >= 1 and len(shpcheckM) >= 1:
        shpCondition = True
        listShapefiles(uitsnedePath, mutatiePath)
    if not gdbCondition and not shpCondition:
        print("(Error) Uploads bevatten niet beide exact 1 .gdb folder OF minimaal 1 .shp file")
        deleteUploads(basePath)

def listGdbfiles(uitsnedePath, mutatiePath):
    layersUitsnede = fiona.listlayers(uitsnedePath)
    layersMutatie = fiona.listlayers(mutatiePath)
    listDifference = set(layersUitsnede).symmetric_difference(layersMutatie)
    if len(listDifference) > 0:
        print("(Error) Verschillende feature classes tussen bestanden: " + str(listDifference))
        deleteUploads(basePath)
    else:
        checkGdbDiff(uitsnedePath, layersUitsnede, mutatiePath, layersMutatie)

def checkGdbDiff(uitsnedePath, layersUitsnede, mutatiePath, layersMutatie):
    outputDf = pd.DataFrame({
                    'DTB_ID': pd.Series(dtype='str'),
                    'NIVEAU': pd.Series(dtype='str'),
                    'TYPE': pd.Series(dtype='str'),
                    'ROTATIE': pd.Series(dtype='str'),
                    'OBJECTTYPE': pd.Series(dtype='str'),
                    'STATUS': pd.Series(dtype='str'),
                    'geometry': pd.Series(dtype='str')
                    })
    outputGdf = gpd.GeoDataFrame(outputDf, crs="EPSG:28992")
    layersMutatie = [layer for layer in layersMutatie if 'DTB_' in layer]
    layersUitsnede = [layer for layer in layersUitsnede if 'DTB_' in layer]
    
    #Compare EVERY layer in both .gdb folders and append new/old/changed features
    for dtbLayer in layersMutatie:
        layerUitsnede = gpd.read_file(uitsnedePath, layer=dtbLayer)
        layerMutatie = gpd.read_file(mutatiePath, layer=dtbLayer)
        layerMutatie['STATUS'] = ''
        layerUitsnede['STATUS'] = ''
    
        layerNew = layerMutatie[~layerMutatie['DTB_ID'].isin(layerUitsnede['DTB_ID'])].copy()
        if not layerNew.empty:
            layerNew.loc[:, 'STATUS'] = 'Nieuw'

        layerDel = layerUitsnede[~layerUitsnede['DTB_ID'].isin(layerMutatie['DTB_ID'])].copy()
        if not layerDel.empty:
            layerDel.loc[:, 'STATUS'] = 'Verwijderd'

        layerMerge = layerMutatie.merge(layerUitsnede, on='DTB_ID', suffixes=('', '_u'))
        layerCompare = layerMerge[layerMerge['geometry_u'] != layerMerge['geometry']]
        layerChange = layerCompare[layerMutatie.columns].copy()
        if not layerChange.empty:
            layerChange.loc[:, 'STATUS'] = 'Veranderd'
        
        layerDifference = gpd.GeoDataFrame(pd.concat([layerNew, layerDel, layerChange], ignore_index=True))
        if not layerDifference.empty:
            layerMatch = [col for col in outputGdf.columns if col in layerDifference.columns]
            outputGdf = gpd.GeoDataFrame(pd.concat([layerDifference[layerMatch], outputGdf], ignore_index=True))
    
    #Output it
    lookupTableFile = os.path.join(scriptDirectory, 'object_conversion.csv')
    lookupTable = pd.read_csv(lookupTableFile, delimiter=',')
    lookupMerge = outputGdf.merge(lookupTable, left_on='TYPE', right_on='TYPE_CODE', how='left')
    totalDifference = lookupMerge.drop(columns=['TYPE_CODE'])
    totalDifference4326 = totalDifference.to_crs(epsg=4326)
    outputPath = os.path.join(basePath, 'data', str(job_id))
    totalDifference4326.to_file(outputPath + '.geojson', driver="GeoJSON")
    print("Verschilkaart maken succesvol afgerond met ID: " + str(job_id))
    deleteUploads(basePath)

def listShapefiles(uitsnedeFolder, mutatieFolder):
    shapesUitsnede = []
    shapesMutatie = []
    shapefilesUitsnede = glob.glob(os.path.join(uitsnedeFolder, "*.shp"))
    shapefilesMutaties = glob.glob(os.path.join(mutatieFolder, "*.shp"))
    for shp in shapefilesUitsnede:
        shapeNameUitsnede = os.path.basename(shp)
        shapesUitsnede.append(shapeNameUitsnede)
    for shp in shapefilesMutaties:
        shapeNameUitsnede = os.path.basename(shp)
        shapesMutatie.append(shapeNameUitsnede)
    listDifference = set(shapesUitsnede).symmetric_difference(shapesMutatie)
    if len(listDifference) > 0:
        print("(Error) Verschillende feature classes tussen bestanden: " + str(listDifference))
        deleteUploads(basePath)
    else:
        checkShpDiff(uitsnedeFolder, mutatieFolder)

def checkShpDiff(uitsnedeFolder, mutatieFolder):
    #Only load shapefile if it exists
    def load_shapefile(folder, filename):
        filepath = os.path.join(folder, filename)
        if os.path.exists(filepath):
            return gpd.read_file(filepath)
        return None
    
    puntU = load_shapefile(uitsnedeFolder, "PUNT.shp")
    lijnU = load_shapefile(uitsnedeFolder, "LIJN.shp")
    vlakU = load_shapefile(uitsnedeFolder, "VLAK.shp")
    puntM = load_shapefile(mutatieFolder, "PUNT.shp")
    lijnM = load_shapefile(mutatieFolder, "LIJN.shp")
    vlakM = load_shapefile(mutatieFolder, "VLAK.shp")
    
    puntDifference = gpd.GeoDataFrame()
    lijnDifference = gpd.GeoDataFrame()
    vlakDifference = gpd.GeoDataFrame()
    
    #New geodataframes for points
    if puntU is not None and puntM is not None:
        puntNew = puntM[~puntM['DTB_ID'].isin(puntU['DTB_ID'])].copy()
        if not puntNew.empty:
            puntNew.loc[:, 'STATUS'] = 'Nieuw'
        
        puntDel = puntU[~puntU['DTB_ID'].isin(puntM['DTB_ID'])].copy()
        if not puntDel.empty:
            puntDel.loc[:, 'STATUS'] = 'Verwijderd'
        
        puntMerge = puntM.merge(puntU, on='DTB_ID', suffixes=('', '_u'))
        puntCompare = puntMerge[puntMerge['geometry_u'] != puntMerge['geometry']]
        puntChange = puntCompare[puntM.columns].copy()
        if not puntChange.empty:
            puntChange.loc[:, 'STATUS'] = 'Veranderd'
        
        puntDifference = gpd.GeoDataFrame(pd.concat([puntNew, puntDel, puntChange], ignore_index=True))
    
    #New geodataframes for lines
    if lijnU is not None and lijnM is not None:
        lijnNew = lijnM[~lijnM['DTB_ID'].isin(lijnU['DTB_ID'])].copy()
        if not lijnNew.empty:
            lijnNew.loc[:, 'STATUS'] = 'Veranderd'

        lijnDel = lijnU[~lijnU['DTB_ID'].isin(lijnM['DTB_ID'])].copy()
        if not lijnDel.empty:
            lijnDel.loc[:, 'STATUS'] = 'Verwijderd'
        
        lijnMerge = lijnM.merge(lijnU, on='DTB_ID', suffixes=('', '_u'))
        lijnCompare = lijnMerge[lijnMerge['geometry_u'] != lijnMerge['geometry']]
        lijnChange = lijnCompare[lijnM.columns].copy()
        if not lijnChange.empty:
            lijnChange.loc[:, 'STATUS'] = 'Veranderd'
        
        lijnDifference = gpd.GeoDataFrame(pd.concat([lijnNew, lijnDel, lijnChange], ignore_index=True))
    
    #New geodataframes for polygons
    if vlakU is not None and vlakM is not None:
        vlakNew = vlakM[~vlakM['DTB_ID'].isin(vlakU['DTB_ID'])].copy()
        if not vlakNew.empty:
            vlakNew.loc[:, 'STATUS'] = 'Nieuw'
        
        vlakDel = vlakU[~vlakU['DTB_ID'].isin(vlakM['DTB_ID'])].copy()
        if not vlakDel.empty:
            vlakDel.loc[:, 'STATUS'] = 'Verwijderd'
        
        vlakMerge = vlakM.merge(vlakU, on='DTB_ID', suffixes=('', '_u'))
        vlakCompare = vlakMerge[vlakMerge['geometry_u'] != vlakMerge['geometry']]
        vlakChange = vlakCompare[vlakM.columns].copy()
        if not vlakChange.empty:
            vlakChange.loc[:, 'STATUS'] = 'Veranderd'
        
        vlakDifference = gpd.GeoDataFrame(pd.concat([vlakNew, vlakDel, vlakChange], ignore_index=True))

    #Samenvoegen eindresultaat en exported naar geojson
    combinedDifference = gpd.GeoDataFrame(pd.concat([puntDifference, lijnDifference, vlakDifference], ignore_index=True))
    lookupTableFile = os.path.join(scriptDirectory, 'object_conversion.csv')
    lookupTable = pd.read_csv(lookupTableFile, delimiter=',')
    lookupMerge = combinedDifference.merge(lookupTable, left_on='CTE', right_on='CTE_CODE', how='left')
    totalDifference = lookupMerge.drop(columns=['CTE_CODE'])
    totalDifference4326 = totalDifference.to_crs(epsg=4326)
    outputPath = os.path.join(basePath, 'data', str(job_id))
    totalDifference4326.to_file(outputPath + '.geojson', driver="GeoJSON")
    print("Verschilkaart maken succesvol afgerond met ID: " + str(job_id))
    deleteUploads(basePath)

def deleteUploads(basePath):
    tempPath = os.path.join(basePath, 'data', 'temp')
    if os.path.exists(tempPath):
        shutil.rmtree(tempPath)
        os.mkdir(tempPath)
    else:
        return

prepareInputdata(basePath, job_id)