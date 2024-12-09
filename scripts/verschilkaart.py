import os
import glob
import geopandas as gpd
import pandas as pd
import sys
import zipfile
import shutil

job_id = sys.argv[1]
#job_id = 909090

scriptDirectory = os.path.dirname(os.path.abspath(__file__))
basePath = os.path.abspath(os.path.join(scriptDirectory, '..'))
#basePath = r"C:\Users\crist\Business\Coding\DTBprojects"

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
    listShapefiles(uitsnedeUnzipPath, mutatieUnzipPath)

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
        checkDiff(uitsnedeFolder, mutatieFolder)

def checkDiff(uitsnedeFolder, mutatieFolder):
    #Define all 3 before-after files to be compared
    puntU = gpd.read_file(os.path.join(uitsnedeFolder, "PUNT.shp"))
    lijnU = gpd.read_file(os.path.join(uitsnedeFolder, "LIJN.shp"))
    vlakU = gpd.read_file(os.path.join(uitsnedeFolder, "VLAK.shp"))
    puntM = gpd.read_file(os.path.join(mutatieFolder, "PUNT.shp"))
    lijnM = gpd.read_file(os.path.join(mutatieFolder, "LIJN.shp"))
    vlakM = gpd.read_file(os.path.join(mutatieFolder, "VLAK.shp"))
    
    #New geodataframes for points
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
    TotalDifference = gpd.GeoDataFrame(pd.concat([puntDifference, lijnDifference, vlakDifference], ignore_index=True))
    TotalDifference4326 = TotalDifference.to_crs(epsg=4326)
    outputPath = os.path.join(basePath, 'data', str(job_id))
    TotalDifference4326.to_file(outputPath + '.geojson', driver="GeoJSON")
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