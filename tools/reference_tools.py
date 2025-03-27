#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramientas para buscar y obtener contexto de propuestas técnicas anteriores.
"""

import os
import re
import json
import logging
import pandas as pd
from pathlib import Path
from langchain_core.tools import tool
from core.execution_tracker import add_to_execution_path

# Configuración del logger
logger = logging.getLogger("TDR_Agente_LangGraph")

# Rutas a los directorios relevantes
REFERENCES_DIR = Path("documentos/Referencias")
PROPOSALS_DIR = Path("documentos/Propuestas")

@tool
def find_similar_proposals(search_params: str) -> str:
    """
    Busca propuestas técnicas similares en el archivo de referencia de Excel.
    
    Args:
        search_params: String en formato JSON con los siguientes campos:
               - section_name: Nombre de la sección que se va a generar
               - tdr_info: Información extraída del TDR actual
        
    Returns:
        JSON con información sobre propuestas similares encontradas
    """
    logger.info("Buscando propuestas técnicas similares")
    
    # Registrar en el historial de ejecución
    add_to_execution_path(
        "find_similar_proposals",
        "Buscando propuestas similares para contexto"
    )
    
    try:
        # Parsear los parámetros
        params_dict = json.loads(search_params)
        section_name = params_dict.get("section_name", "")
        tdr_info = params_dict.get("tdr_info", "")
        
        # Extraer palabras clave del TDR y nombre de sección para la búsqueda
        keywords = extract_keywords(tdr_info, section_name)
        logger.info(f"Palabras clave extraídas: {keywords}")
        
        # Encontrar el archivo Excel de referencias
        excel_path = find_reference_excel()
        if not excel_path:
            return json.dumps({
                "status": "error",
                "message": "No se encontró el archivo Excel de referencias",
                "proposals": []
            })
        
        # Leer el Excel y buscar propuestas similares
        references = read_reference_excel(excel_path)
        # Corregido: verificar si references es None o está vacío de forma segura
        if references is None or (isinstance(references, pd.DataFrame) and references.empty):
            return json.dumps({
                "status": "error",
                "message": "No se pudieron cargar referencias del Excel",
                "proposals": []
            })
        
        # Buscar propuestas similares basadas en palabras clave
        similar_proposals = find_matching_proposals(references, keywords)
        
        if not similar_proposals:
            return json.dumps({
                "status": "warning",
                "message": "No se encontraron propuestas similares",
                "proposals": []
            })
        
        # Extraer contenido relevante de las propuestas
        enriched_proposals = []
        for prop in similar_proposals:
            proposal_content = extract_proposal_content(prop, section_name)
            if proposal_content:
                enriched_proposals.append({
                    "project_code": prop.get("codigo_proyecto", ""),
                    "project_name": prop.get("nombre_proyecto", ""),
                    "section_content": proposal_content,
                    "similarity_score": prop.get("similarity_score", 0)
                })
        
        return json.dumps({
            "status": "success",
            "message": f"Se encontraron {len(enriched_proposals)} propuestas similares",
            "proposals": enriched_proposals
        })
        
    except Exception as e:
        error_message = f"Error al buscar propuestas similares: {str(e)}"
        logger.error(error_message, exc_info=True)
        
        # Registrar error
        add_to_execution_path(
            "find_similar_proposals_error",
            error_message
        )
        
        return json.dumps({
            "status": "error",
            "message": error_message,
            "proposals": []
        })

def extract_keywords(tdr_info: str, section_name: str) -> list:
    """
    Extrae palabras clave relevantes del TDR y el nombre de la sección.
    
    Args:
        tdr_info: Información extraída del TDR
        section_name: Nombre de la sección
        
    Returns:
        Lista de palabras clave
    """
    # Convertir a minúsculas
    tdr_info_lower = tdr_info.lower()
    section_name_lower = section_name.lower()
    
    # Intentar extraer el título del proyecto y otras palabras clave
    keywords = []
    
    # Intentar extraer JSON si es posible
    try:
        info_dict = json.loads(tdr_info)
        
        # Extraer título y palabras clave
        if "titulo_proyecto" in info_dict:
            title_words = info_dict["titulo_proyecto"].lower().split()
            keywords.extend([word for word in title_words if len(word) > 3])
        
        # Extraer algunas palabras clave de requisitos técnicos
        if "requisitos_tecnicos" in info_dict:
            req_text = info_dict["requisitos_tecnicos"].lower()
            # Buscar términos técnicos comunes
            tech_keywords = ["web", "móvil", "cloud", "seguridad", "api", 
                            "inteligencia artificial", "machine learning", "base de datos",
                            "desarrollo", "infraestructura", "red", "hardware", "software"]
            
            for keyword in tech_keywords:
                if keyword in req_text:
                    keywords.append(keyword)
    except:
        # Si no es JSON, extraer palabras clave del texto
        # Extraer palabras clave de secciones específicas
        try:
            # Buscar título del proyecto
            title_match = re.search(r"título del proyecto[:\s]+(.*?)(?:\n|$)", tdr_info_lower)
            if title_match:
                title_words = title_match.group(1).split()
                keywords.extend([word for word in title_words if len(word) > 3])
        except:
            pass
    
    # Añadir palabras clave de la sección
    section_words = section_name_lower.split()
    keywords.extend([word for word in section_words if len(word) > 3])
    
    # Eliminar duplicados y palabras comunes
    common_words = ["para", "como", "esta", "este", "estos", "estas", "que", "los", "las", "del", "con"]
    keywords = [word for word in keywords if word not in common_words]
    
    # Eliminar duplicados
    return list(set(keywords))

def find_reference_excel() -> str:
    """
    Busca el archivo Excel de referencias en la carpeta especificada.
    
    Returns:
        Ruta al archivo Excel o None si no se encuentra
    """
    try:
        # Verificar si el directorio existe
        if not os.path.exists(REFERENCES_DIR):
            logger.warning(f"Directorio de referencias no encontrado: {REFERENCES_DIR}")
            return None
        
        # Buscar archivos Excel
        excel_files = list(REFERENCES_DIR.glob("*.xlsx"))
        if not excel_files:
            excel_files = list(REFERENCES_DIR.glob("*.xls"))
        
        if not excel_files:
            logger.warning(f"No se encontraron archivos Excel en {REFERENCES_DIR}")
            return None
        
        # Devolver el primer archivo Excel encontrado
        return str(excel_files[0])
    except Exception as e:
        logger.error(f"Error al buscar archivo Excel de referencias: {str(e)}", exc_info=True)
        return None

def read_reference_excel(excel_path: str) -> pd.DataFrame:
    """
    Lee el archivo Excel de referencias y extrae la información relevante.
    
    Args:
        excel_path: Ruta al archivo Excel
        
    Returns:
        DataFrame con la información de propuestas anteriores
    """
    try:
        # Leer el Excel - intentar leer la página 3 primero
        try:
            df = pd.read_excel(excel_path, sheet_name=2)  # 0-indexed, así que sheet 3 es index 2
        except:
            # Si falla, intentar leer la primera página
            df = pd.read_excel(excel_path)
        
        return df
    except Exception as e:
        logger.error(f"Error al leer Excel de referencias: {str(e)}", exc_info=True)
        return None

def find_matching_proposals(references: pd.DataFrame, keywords: list) -> list:
    """
    Encuentra propuestas que coincidan con las palabras clave.
    
    Args:
        references: DataFrame con la información de propuestas
        keywords: Lista de palabras clave a buscar
        
    Returns:
        Lista de propuestas coincidentes con puntuación de similitud
    """
    matching_proposals = []
    
    # Verificar las columnas disponibles
    expected_columns = ["codigo_proyecto", "nombre_proyecto", "palabras_clave", "ruta_archivo"]
    available_columns = references.columns.tolist()
    
    # Mapear columnas reales a columnas esperadas
    column_mapping = {}
    for exp_col in expected_columns:
        # Buscar coincidencia exacta
        if exp_col in available_columns:
            column_mapping[exp_col] = exp_col
            continue
        
        # Buscar coincidencia parcial (ignorando mayúsculas/minúsculas)
        exp_col_lower = exp_col.lower()
        for col in available_columns:
            if exp_col_lower in col.lower():
                column_mapping[exp_col] = col
                break
    
    # Si no se encontraron las columnas principales, salir
    required_columns = ["codigo_proyecto", "nombre_proyecto", "ruta_archivo"]
    for col in required_columns:
        if col not in column_mapping:
            logger.warning(f"Columna requerida no encontrada: {col}")
            return []
    
    # Convertir a lista de diccionarios para procesamiento
    proposals = references.to_dict(orient='records')
    
    for prop in proposals:
        score = 0
        
        # Verificar coincidencia en código de proyecto
        project_code = str(prop.get(column_mapping.get("codigo_proyecto", ""), "")).lower()
        if project_code:
            for keyword in keywords:
                if keyword in project_code:
                    score += 5  # Mayor peso para coincidencias en código
        
        # Verificar coincidencia en nombre de proyecto
        project_name = str(prop.get(column_mapping.get("nombre_proyecto", ""), "")).lower()
        if project_name:
            for keyword in keywords:
                if keyword in project_name:
                    score += 3  # Peso medio para coincidencias en nombre
        
        # Verificar coincidencia en palabras clave si existe la columna
        if "palabras_clave" in column_mapping:
            keyword_field = str(prop.get(column_mapping.get("palabras_clave", ""), "")).lower()
            if keyword_field:
                for keyword in keywords:
                    if keyword in keyword_field:
                        score += 2  # Peso menor para coincidencias en palabras clave
        
        # Si hay suficiente coincidencia, añadir a la lista
        if score > 0:
            matched_prop = {
                "codigo_proyecto": prop.get(column_mapping.get("codigo_proyecto", ""), ""),
                "nombre_proyecto": prop.get(column_mapping.get("nombre_proyecto", ""), ""),
                "ruta_archivo": prop.get(column_mapping.get("ruta_archivo", ""), ""),
                "similarity_score": score
            }
            matching_proposals.append(matched_prop)
    
    # Ordenar por puntuación de similitud (mayor a menor)
    matching_proposals.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    # Limitar a las 5 propuestas más relevantes
    return matching_proposals[:5]

def extract_proposal_content(proposal: dict, section_name: str) -> str:
    """
    Extrae el contenido relevante de una propuesta previa para la sección específica.
    
    Args:
        proposal: Información de la propuesta
        section_name: Nombre de la sección
        
    Returns:
        Contenido extraído para la sección o cadena vacía si no se encuentra
    """
    try:
        # Construir la ruta al archivo de propuesta
        project_code = proposal.get("codigo_proyecto", "")
        file_path = proposal.get("ruta_archivo", "")
        
        # Si la ruta no es absoluta, construirla relativa al directorio de propuestas
        if not os.path.isabs(file_path):
            file_path = os.path.join(PROPOSALS_DIR, file_path)
        
        # Si no existe, buscar por código de proyecto
        if not os.path.exists(file_path):
            # Buscar archivos que contengan el código de proyecto
            potential_files = []
            
            if os.path.exists(PROPOSALS_DIR):
                for root, dirs, files in os.walk(PROPOSALS_DIR):
                    for file in files:
                        if project_code in file and (file.endswith('.txt') or file.endswith('.md')):
                            potential_files.append(os.path.join(root, file))
            
            if not potential_files:
                logger.warning(f"No se encontraron archivos para el código de proyecto: {project_code}")
                return ""
            
            # Usar el primer archivo encontrado
            file_path = potential_files[0]
        
        # Verificar si el archivo existe
        if not os.path.exists(file_path):
            logger.warning(f"Archivo de propuesta no encontrado: {file_path}")
            return ""
        
        # Leer el contenido del archivo
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Buscar la sección específica en el contenido
        section_pattern = get_section_pattern(section_name)
        
        # Intentar encontrar la sección
        section_content = ""
        match = re.search(section_pattern, content, re.IGNORECASE | re.DOTALL)
        
        if match:
            section_content = match.group(1).strip()
            
            # Limitar el contenido a un tamaño razonable (5000 caracteres)
            if len(section_content) > 5000:
                section_content = section_content[:5000] + "..."
        else:
            logger.warning(f"Sección '{section_name}' no encontrada en {file_path}")
        
        return section_content
    
    except Exception as e:
        logger.error(f"Error al extraer contenido de propuesta: {str(e)}", exc_info=True)
        return ""

def get_section_pattern(section_name: str) -> str:
    """
    Genera un patrón regex para encontrar la sección específica.
    
    Args:
        section_name: Nombre de la sección a buscar
        
    Returns:
        Patrón regex para encontrar la sección
    """
    # Normalizar el nombre de la sección
    section_name_lower = section_name.lower()
    
    # Mapear nombre de sección a posibles encabezados
    section_mappings = {
        "introduccion": ["introducción", "introduccion", "1\\.", "i\\.", "1 "],
        "objetivos": ["objetivos", "2\\.", "ii\\.", "2 "],
        "alcance": ["alcance", "3\\.", "iii\\.", "3 "],
        "metodologia": ["metodología", "metodologia", "4\\.", "iv\\.", "4 "],
        "plan": ["plan", "cronograma", "5\\.", "v\\.", "5 "],
        "entregables": ["entregables", "6\\.", "vi\\.", "6 "],
        "recursos": ["recursos", "7\\.", "vii\\.", "7 "],
        "riesgos": ["riesgos", "8\\.", "viii\\.", "8 "],
        "calidad": ["calidad", "9\\.", "ix\\.", "9 "]
    }
    
    # Buscar coincidencias en el mapeo
    header_options = []
    for key, alternatives in section_mappings.items():
        if key in section_name_lower:
            header_options.extend(alternatives)
    
    # Si no hay coincidencias, usar el nombre de la sección
    if not header_options:
        header_options = [re.escape(section_name)]
    
    # Construir el patrón de búsqueda
    header_pattern = "|".join([f"{opt}" for opt in header_options])
    
    # Patrón para encontrar la sección y capturar su contenido hasta la siguiente sección
    return f"(?:##?\\s*|\\b)({header_pattern})(?:[ \t:]+|[ \t]*\\n)([^#]*)(?:##|$)"