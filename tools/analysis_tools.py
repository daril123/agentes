#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Herramientas para análisis del TDR y generación de estructura.
"""

import json
import logging
import re
from langchain_core.tools import tool
from core.execution_tracker import add_to_execution_path
from llm.model import get_llm

# Configuración del logger
logger = logging.getLogger("TDR_Agente_LangGraph")

@tool
def analyze_tdr(text: str) -> str:
    """
    Usa el modelo LLM para extraer información clave del TDR.
    
    Args:
        text: Texto del TDR
        
    Returns:
        Información extraída del TDR en formato JSON
    """
    logger.info("Analizando el TDR")
    
    # Registrar en el historial de ejecución
    add_to_execution_path(
        "analyze_tdr",
        "Extrayendo información clave del TDR"
    )
    
    try:
        llm = get_llm()
        prompt = (
            "Extrae la siguiente información del TDR (Términos de Referencia):\n"
            "- Título del proyecto\n"
            "- Alcance del proyecto\n"
            "- Lista de entregables\n"
            "- Materiales y equipos requeridos\n"
            "- Lista de actividades\n"
            "- Normativas mencionadas\n"
            "- Plazos y cronogramas\n"
            "- Requisitos técnicos específicos\n"
            "- Criterios de evaluación\n\n"
            "Responde en formato JSON con claves en español.\n\n"
            f"TDR:\n{text}"  # Limitar a los primeros 10000 caracteres
        )
        
        response = llm.invoke(prompt)
        
        # Limpiar la respuesta si contiene delimitadores de código
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
        
        logger.info(f"Análisis del TDR completado: {response[:200]}...")
        
        # Registrar éxito
        add_to_execution_path(
            "analyze_tdr_result",
            "Análisis completado exitosamente"
        )
        
        return response
    except Exception as e:
        error_message = f"Error al analizar el TDR: {str(e)}"
        logger.error(error_message)
        
        # Registrar error
        add_to_execution_path(
            "analyze_tdr_error",
            error_message
        )
        
        return f"Error: {error_message}"

@tool
def generate_index(info: str) -> str:
    """
    Genera un índice para la propuesta técnica basado en la información extraída.
    
    Args:
        info: Información extraída del TDR
        
    Returns:
        Índice en formato JSON
    """
    logger.info("Generando índice para la propuesta técnica")
    
    # Registrar en el historial de ejecución
    add_to_execution_path(
        "generate_index",
        "Generando estructura e índice de la propuesta"
    )
    
    try:
        llm = get_llm()
        prompt = (
            "Con la siguiente información extraída del TDR, genera un índice para la propuesta técnica. "
            "Cada sección debe ser una clave y su valor, una breve descripción de lo que contendrá. "
            "El índice DEBE incluir obligatoriamente las siguientes secciones según los requisitos del documento proporcionado:\n\n"
            "1. Introducción y contexto del proyecto\n"
            "2. Objetivos (general y específicos)\n"
            "3. Alcance detallado del trabajo\n"
            "4. Metodología propuesta\n"
            "5. Plan de trabajo y cronograma\n"
            "6. Entregables con descripción detallada\n"
            "7. Recursos humanos y técnicos asignados\n"
            "8. Gestión de riesgos\n"
            "9. Plan de calidad\n"
            "10. Normativas y estándares aplicables\n"
            "11. Experiencia relevante en proyectos similares\n"
            "12. Anexos técnicos\n\n"
            "Devuelve la respuesta únicamente en formato JSON sin ningún texto adicional.\n\n"
            "Información:\n"
            f"{info}\n\n"
            "Responde en formato JSON. Es sumamente urgente que estructures esto en formato json "
        )
        
        response = llm.invoke(prompt)

        # Limpiar la respuesta si contiene delimitadores de código
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        # Validar que sea un JSON válido
        try:
            json_response = json.loads(response)
            response = json.dumps(json_response)
        except json.JSONDecodeError:
            logger.warning("La respuesta no es un JSON válido. Intentando reparar...")
            # Intentar reparar JSON
            response = re.sub(r',\s*}', '}', response)
            response = re.sub(r',\s*]', ']', response)
            # Asegurar que esté entre llaves
            if not response.strip().startswith("{"):
                response = "{" + response
            if not response.strip().endswith("}"):
                response = response + "}"
            
        logger.info(f"Índice generado: {response[:200]}...")
        
        # Registrar éxito
        add_to_execution_path(
            "generate_index_result",
            "Índice generado exitosamente"
        )
        
        return response
    except Exception as e:
        error_message = f"Error al generar índice: {str(e)}"
        logger.error(error_message)
        
        # Registrar error
        add_to_execution_path(
            "generate_index_error",
            error_message
        )
        
        return f"Error: {error_message}"