@echo off
@break off
@title Creating a folder - D3F4ULT
@color 0a
@cls

setlocal EnableDelayedExpansion

if not exist "data" (
  mkdir "data"
  if "!errorlevel!" EQU "0" (
    echo Folder created successfully
  ) else (
    echo Error while creating folder
  )
) else (
  echo Folder already exists
)

@title Running the python script - D3F4ULT

setlocal EnableDelayedExpansion
@py.exe src\CollectFiles.py %*
@pause