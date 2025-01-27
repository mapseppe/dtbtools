import os
import glob
import geopandas as gpd
import pandas as pd
import sys
import zipfile
import shutil
import fiona
import shapely

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
    missing_layers = set(layersUitsnede) - set(layersMutatie)
    missing_layers.discard('AOI')
    if missing_layers:
        print(f"(Error) Niet alle layers aanwezig in mutatie upload, waaronder: {missing_layers}")
        deleteUploads(basePath)
    else:
        checkGdbDiff(uitsnedePath, layersUitsnede, mutatiePath, layersMutatie)
    
def checkGdbDiff(uitsnedePath, layersUitsnede, mutatiePath, layersMutatie):
    outputDf = pd.DataFrame({
                    'DTB_ID': pd.Series(dtype='str'),
                    'NIVEAU': pd.Series(dtype='str'),
                    'TYPE': pd.Series(dtype='str'),
                    'ROTATIE': pd.Series(dtype='str'),
                    'STATUS': pd.Series(dtype='str'),
                    'geometry': pd.Series(dtype='str'),
                    'TYPE_o': pd.Series(dtype='str'),
                    })
    outputGdf = gpd.GeoDataFrame(outputDf, crs="EPSG:28992")
    layersMutatie = [layer for layer in layersMutatie if 'DTB_' in layer]
    layersUitsnede = [layer for layer in layersUitsnede if 'DTB_' in layer]
    
    #Compare EVERY layer in both .gdb folders and append new/old/changed features
    for dtbLayer in layersUitsnede:
        layerUitsnede = gpd.read_file(uitsnedePath, layer=dtbLayer)
        layerMutatie = gpd.read_file(mutatiePath, layer=dtbLayer)
        layerUitsnede.geometry = shapely.set_precision(layerUitsnede.geometry, grid_size=0.001)
        layerMutatie.geometry = shapely.set_precision(layerMutatie.geometry, grid_size=0.001)
        layerMutatie['STATUS'] = ''
        layerUitsnede['STATUS'] = ''
        layerMutatie['TYPE_o'] = ''
        layerUitsnede['TYPE_o'] = ''
        
        layerChangeNewF = gpd.GeoDataFrame(columns=layerMutatie.columns)
        layerChangeOldF = gpd.GeoDataFrame(columns=layerMutatie.columns)
        layerChange = gpd.GeoDataFrame(columns=layerMutatie.columns)
        #Check new features
        layerNew = layerMutatie[~layerMutatie['DTB_ID'].isin(layerUitsnede['DTB_ID'])].copy()
        if not layerNew.empty:
            layerNew.loc[:, 'STATUS'] = 'Nieuw'

        #Check deleted features
        layerDel = layerUitsnede[~layerUitsnede['DTB_ID'].isin(layerMutatie['DTB_ID'])].copy()
        if not layerDel.empty:
            layerDel.loc[:, 'STATUS'] = 'Verwijderd'
            layerDel['TYPE_o'] = layerDel['TYPE']
            layerDel['TYPE'] = ''

        #Check changed features
        #Compare area if its a polygon layer
        if layerMutatie.geom_type.isin(['Polygon']).all():
            layerMutatie['area'] = layerMutatie.geometry.area
            layerUitsnede['area'] = layerUitsnede.geometry.area
            layerMerge = layerMutatie.merge(layerUitsnede, on='DTB_ID', how='inner', suffixes=('', '_u'))
            layerCompare = layerMerge[layerMerge['area_u'] != layerMerge['area']]
        #Compare geometry if its a line or point layer
        else:
            layerMerge = layerMutatie.merge(layerUitsnede, on='DTB_ID', how='inner', suffixes=('', '_u'))
            layerCompare = layerMerge[layerMerge['geometry_u'] != layerMerge['geometry']]
        
        if not layerCompare.empty:
            layerCompare.loc[:, 'TYPE_o'] = layerCompare['TYPE_u']
            layerChange = layerCompare.copy()
            layerChange.loc[:, 'STATUS'] = 'Veranderd'
            layerChangeNew = layerCompare.copy()
            layerChangeOld = layerCompare.copy()
            layerChangeNew['geometry'] = layerChangeNew.apply(lambda row: row['geometry'].difference(row['geometry_u']), axis=1)
            layerChangeOld['geometry'] = layerChangeOld.apply(lambda row: row['geometry_u'].difference(row['geometry']), axis=1)
            layerChangeNewF = layerChangeNew[layerMutatie.columns].copy()
            layerChangeOldF = layerChangeOld[layerMutatie.columns].copy()
            layerChangeNewF = layerChangeNewF[~layerChangeNewF['geometry'].is_empty]
            layerChangeOldF = layerChangeOldF[~layerChangeOldF['geometry'].is_empty]
            layerChangeNewF.loc[:, 'STATUS'] = 'Veranderd Nieuw'
            layerChangeOldF.loc[:, 'STATUS'] = 'Veranderd Oud'
        
        #Process the total changes of layer
        layerDifference = gpd.GeoDataFrame(pd.concat([layerNew, layerDel, layerChange, layerChangeNewF, layerChangeOldF], ignore_index=True))
        if not layerDifference.empty:
            common_columns = [col for col in outputGdf.columns if col in layerDifference.columns]
            layerDifference = layerDifference[common_columns].copy()
            outputGdf = gpd.GeoDataFrame(pd.concat([layerDifference, outputGdf], ignore_index=True))
    
    #Output it
    lookupTableFile = os.path.join(scriptDirectory, 'object_conversion.csv')
    lookupTable = pd.read_csv(lookupTableFile, delimiter=',')
    lookupTable_unique = lookupTable.drop_duplicates(subset='TYPE_CODE')
    combinedDifference = outputGdf.merge(
        lookupTable_unique[['TYPE_CODE', 'TYPE_OMSCHRIJVING']], 
        left_on='TYPE_o', 
        right_on='TYPE_CODE', 
        how='left'
    ).rename(columns={'TYPE_OMSCHRIJVING': 'TYPE_oud'})
    combinedDifference = combinedDifference.merge(
        lookupTable_unique[['TYPE_CODE', 'TYPE_OMSCHRIJVING']], 
        left_on='TYPE', 
        right_on='TYPE_CODE', 
        how='left'
    ).rename(columns={'TYPE_OMSCHRIJVING': 'TYPE_nieuw'})
    totalDifference4326 = combinedDifference.to_crs(epsg=4326)
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
        if shapeNameUitsnede != 'AOI.shp':
            shapesUitsnede.append(shapeNameUitsnede)
    for shp in shapefilesMutaties:
        shapeNameMutatie = os.path.basename(shp)
        if shapeNameMutatie != 'AOI.shp':
            shapesMutatie.append(shapeNameMutatie)
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
            gdf = gpd.read_file(filepath)
            gdf.geometry = shapely.set_precision(gdf.geometry, grid_size=0.001)
            return gdf
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
        puntM['CTE_oud'] = ''
        puntNew = puntM[~puntM['DTB_ID'].isin(puntU['DTB_ID'])].copy()
        if not puntNew.empty:
            puntNew.loc[:, 'STATUS'] = 'Nieuw'
        
        puntDel = puntU[~puntU['DTB_ID'].isin(puntM['DTB_ID'])].copy()
        if not puntDel.empty:
            puntDel.loc[:, 'STATUS'] = 'Verwijderd'
            puntDel.loc[:, 'CTE_oud'] = puntDel['CTE']
            puntDel.loc[:, 'CTE'] = ''
        
        puntMerge = puntM.merge(puntU, on='DTB_ID', how='inner', suffixes=('', '_u'))
        puntCompare = puntMerge[puntMerge['geometry_u'] != puntMerge['geometry']]
        if not puntCompare.empty:
            puntCompare.loc[:, 'CTE_oud'] = puntCompare['CTE_u']
            puntChange = puntCompare[puntM.columns].copy()
            puntChange.loc[:, 'STATUS'] = 'Veranderd'
            puntChangeNew = puntCompare.copy()
            puntChangeOld = puntCompare.copy()
            puntChangeNew['geometry'] = puntCompare.apply(lambda row: row['geometry'].difference(row['geometry_u']), axis=1)
            puntChangeOld['geometry'] = puntCompare.apply(lambda row: row['geometry_u'].difference(row['geometry']), axis=1)
            puntChangeNewF = puntChangeNew[puntM.columns].copy()
            puntChangeOldF = puntChangeOld[puntM.columns].copy()
            puntChangeNewF = puntChangeNewF[~puntChangeNewF['geometry'].is_empty]
            puntChangeOldF = puntChangeOldF[~puntChangeOldF['geometry'].is_empty]
            puntChangeNewF.loc[:, 'STATUS'] = 'Veranderd Nieuw'
            puntChangeOldF.loc[:, 'STATUS'] = 'Veranderd Oud'
        
        if 'puntChangeNewF' not in locals():
            puntChangeNewF = gpd.GeoDataFrame(columns=puntM.columns)
        if 'puntChangeOldF' not in locals():
            puntChangeOldF = gpd.GeoDataFrame(columns=puntM.columns)
        if 'puntChange' not in locals():
            puntChange = gpd.GeoDataFrame(columns=puntM.columns)
        
        puntDifference = gpd.GeoDataFrame(pd.concat([puntNew, puntDel, puntChange, puntChangeNewF, puntChangeOldF], ignore_index=True))
    
    #New geodataframes for lines
    if lijnU is not None and lijnM is not None:
        lijnChangeNewF = gpd.GeoDataFrame(columns=lijnM.columns)
        lijnChangeOldF = gpd.GeoDataFrame(columns=lijnM.columns)
        lijnChange = gpd.GeoDataFrame(columns=lijnM.columns)
        lijnM['CTE_oud'] = ''
        lijnNew = lijnM[~lijnM['DTB_ID'].isin(lijnU['DTB_ID'])].copy()
        if not lijnNew.empty:
            lijnNew.loc[:, 'STATUS'] = 'Nieuw'

        lijnDel = lijnU[~lijnU['DTB_ID'].isin(lijnM['DTB_ID'])].copy()
        if not lijnDel.empty:
            lijnDel.loc[:, 'STATUS'] = 'Verwijderd'
            lijnDel.loc[:, 'CTE_oud'] = lijnDel['CTE']
            lijnDel.loc[:, 'CTE'] = ''
        
        lijnMerge = lijnM.merge(lijnU, on='DTB_ID', how='inner', suffixes=('', '_u'))
        lijnCompare = lijnMerge[lijnMerge['geometry_u'] != lijnMerge['geometry']]
        if not lijnCompare.empty:
            lijnCompare.loc[:, 'CTE_oud'] = lijnCompare['CTE_u']
            lijnChange = lijnCompare[lijnM.columns].copy()
            lijnChange.loc[:, 'STATUS'] = 'Veranderd'
            lijnChangeNew = lijnCompare.copy()
            lijnChangeOld = lijnCompare.copy()
            lijnChangeNew['geometry'] = lijnCompare.apply(lambda row: row['geometry'].difference(row['geometry_u']), axis=1)
            lijnChangeOld['geometry'] = lijnCompare.apply(lambda row: row['geometry_u'].difference(row['geometry']), axis=1)
            lijnChangeNewF = lijnChangeNew[lijnM.columns].copy()
            lijnChangeOldF = lijnChangeOld[lijnM.columns].copy()
            lijnChangeNewF = lijnChangeNewF[~lijnChangeNewF['geometry'].is_empty]
            lijnChangeOldF = lijnChangeOldF[~lijnChangeOldF['geometry'].is_empty]
            lijnChangeNewF.loc[:, 'STATUS'] = 'Veranderd Nieuw'
            lijnChangeOldF.loc[:, 'STATUS'] = 'Veranderd Oud'

        lijnDifference = gpd.GeoDataFrame(pd.concat([lijnNew, lijnDel, lijnChange, lijnChangeNewF, lijnChangeOldF], ignore_index=True))
    
    #New geodataframes for polygons
    if vlakU is not None and vlakM is not None:
        vlakChangeNewF = gpd.GeoDataFrame(columns=vlakM.columns)
        vlakChangeOldF = gpd.GeoDataFrame(columns=vlakM.columns)
        vlakChange = gpd.GeoDataFrame(columns=vlakM.columns)
        vlakU = vlakU[vlakU['LAYER'] == 1]
        vlakM = vlakM[vlakM['LAYER'] == 1]
        vlakM['CTE_oud'] = ''
        vlakU['area'] = vlakU.geometry.area
        vlakM['area'] = vlakM.geometry.area
        vlakNew = vlakM[~vlakM['DTB_ID'].isin(vlakU['DTB_ID'])].copy()
        if not vlakNew.empty:
            vlakNew.loc[:, 'STATUS'] = 'Nieuw'
        
        vlakDel = vlakU[~vlakU['DTB_ID'].isin(vlakM['DTB_ID'])].copy()
        if not vlakDel.empty:
            vlakDel.loc[:, 'STATUS'] = 'Verwijderd'
            vlakDel.loc[:, 'CTE_oud'] = vlakDel['CTE']
            vlakDel.loc[:, 'CTE'] = ''
        
        vlakMerge = vlakM.merge(vlakU, on='DTB_ID', how='inner', suffixes=('', '_u'))
        vlakCompare = vlakMerge[vlakMerge['area_u'] != vlakMerge['area']]
        if not vlakCompare.empty:
            vlakCompare['CTE_oud'] = vlakCompare['CTE_u']
            vlakChange = vlakCompare[vlakM.columns].copy()
            vlakChange.loc[:, 'STATUS'] = 'Veranderd'
            vlakChangeNew = vlakCompare.copy()
            vlakChangeOld = vlakCompare.copy()
            vlakChangeNew['geometry'] = vlakCompare.apply(lambda row: row['geometry'].difference(row['geometry_u']), axis=1)
            vlakChangeOld['geometry'] = vlakCompare.apply(lambda row: row['geometry_u'].difference(row['geometry']), axis=1)
            vlakChangeNewF = vlakChangeNew[vlakM.columns].copy()
            vlakChangeOldF = vlakChangeOld[vlakM.columns].copy()
            vlakChangeNewF = vlakChangeNewF[~vlakChangeNewF['geometry'].is_empty]
            vlakChangeOldF = vlakChangeOldF[~vlakChangeOldF['geometry'].is_empty]
            vlakChangeNewF.loc[:, 'STATUS'] = 'Veranderd Nieuw'
            vlakChangeOldF.loc[:, 'STATUS'] = 'Veranderd Oud'
            
        vlakDifference = gpd.GeoDataFrame(pd.concat([vlakNew, vlakDel, vlakChange, vlakChangeNewF, vlakChangeOldF], ignore_index=True))

    #Samenvoegen eindresultaat en exported naar geojson
    combinedDifference = gpd.GeoDataFrame(pd.concat([puntDifference, lijnDifference, vlakDifference], ignore_index=True))
    lookupTableFile = os.path.join(scriptDirectory, 'object_conversion.csv')
    lookupTable = pd.read_csv(lookupTableFile, delimiter=',')
    lookupTable_unique = lookupTable.drop_duplicates(subset='CTE_CODE')
    combinedDifference = combinedDifference.merge(
        lookupTable_unique[['CTE_CODE', 'TYPE_OMSCHRIJVING']], 
        left_on='CTE_oud', 
        right_on='CTE_CODE', 
        how='left'
    ).rename(columns={'TYPE_OMSCHRIJVING': 'TYPE_oud'})
    combinedDifference = combinedDifference.merge(
        lookupTable_unique[['CTE_CODE', 'TYPE_OMSCHRIJVING']], 
        left_on='CTE', 
        right_on='CTE_CODE', 
        how='left'
    ).rename(columns={'TYPE_OMSCHRIJVING': 'TYPE_nieuw'})
    totalDifference4326 = combinedDifference.to_crs(4326)
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