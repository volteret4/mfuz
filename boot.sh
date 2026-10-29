#!/usr/bin/env bash
# -*- coding: utf-8 -*-

source $HOME/Scripts/python_venv/bin/activate
cd $HOME/gits/pollo/music-fuzzy
# Instala la última db que trajo Syncthing de pepecono (solo si la app está cerrada)
./actualizar_db.py traer
python3 $HOME/gits/pollo/music-fuzzy/main.py $HOME/gits/pollo/music-fuzzy/config/config.yml