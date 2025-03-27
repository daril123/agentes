#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nodo para generar el índice de la propuesta técnica.
"""

import json
import logging
from langchain_core.messages import AIMessage
from core.state import TDRAgentState, format_state_for_log
from core.execution_tracker import add_to_execution_path
from tools.analysis_tools import generate_index
import re
# Configuración del logger
logger = logging.getLogger("TDR_Agente_LangGraph")

def generate_index_node(state: TDRAgentState) -> TDRAgentState:
    """
    Genera el índice para la propuesta técnica.
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado actualizado con el índice de la propuesta
    """
    logger.info(f"Iniciando generate_index_node con estado: {format_state_for_log(state)}")
    
    # Registrar inicio del nodo
    add_to_execution_path(
        "generate_index_node",
        "Nodo de generación del índice"
    )
    
    # Verificar que exista la información del TDR
    tdr_info = state.get("tdr_info")
    if not tdr_info:
        logger.error("No hay información del TDR para generar el índice")
        state["messages"].append(AIMessage(content="Error: No hay información del TDR para generar el índice"))
        state["next_step"] = "end"
        return state
    
    # Generar el índice
    index_str = generate_index(tdr_info)
    if index_str.startswith("Error:"):
        logger.error(f"Error al generar índice: {index_str}")
        state["messages"].append(AIMessage(content=index_str))
        state["next_step"] = "end"
        return state
    
    try:
        # Convertir el índice a diccionario
        index_dict = json.loads(index_str)
        
        # Guardar el índice en el estado
        state["index"] = index_dict
        state["sections"] = []  # Inicializar lista de secciones
        state["current_section_index"] = 0  # Inicializar índice para generar secciones
        
        # Crear una lista con los nombres de las secciones
        section_names = list(index_dict.keys())
        
        logger.info(f"Índice generado con {len(section_names)} secciones")
        
        # Actualizar el mensaje en el historial
        index_summary = ", ".join(section_names[:5])
        if len(section_names) > 5:
            index_summary += f", y {len(section_names) - 5} más"
        
        state["messages"].append(AIMessage(content=f"Índice generado exitosamente con las siguientes secciones: {index_summary}"))
        
        # Siguiente paso
        state["next_step"] = "generate_sections"
        
    except json.JSONDecodeError as e:
        error_message = f"Error al decodificar el índice JSON: {str(e)}, índice: {index_str[:200]}..."
        logger.error(error_message)
        
        # Intentar reparar el JSON antes de fallar
        try:
            # Limpieza básica de JSON
            fixed_index_str = re.sub(r',\s*}', '}', index_str)
            fixed_index_str = re.sub(r',\s*]', ']', fixed_index_str)
            
            # Intentar cargar el JSON reparado
            index_dict = json.loads(fixed_index_str)
            
            # Si llegamos aquí, la reparación funcionó
            logger.info("JSON reparado exitosamente")
            state["index"] = index_dict
            state["sections"] = []
            state["current_section_index"] = 0
            
            section_names = list(index_dict.keys())
            index_summary = ", ".join(section_names[:5])
            if len(section_names) > 5:
                index_summary += f", y {len(section_names) - 5} más"
            
            state["messages"].append(AIMessage(content=f"Índice reparado y generado con las siguientes secciones: {index_summary}"))
            
            # Siguiente paso
            state["next_step"] = "generate_sections"
            
        except Exception as e2:
            # Si la reparación también falla, entonces terminamos
            logger.error(f"Error al intentar reparar el JSON: {str(e2)}")
            state["messages"].append(AIMessage(content=f"Error: {error_message}"))
            state["next_step"] = "end"
    
    logger.info(f"Estado después de generate_index_node: {format_state_for_log(state)}")
    return state
