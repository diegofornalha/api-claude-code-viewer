#!/usr/bin/env python3
"""
🛠️ Streamlit Debug Interface - Viewer Claude Session Summarizer
Interface de debug para testar e monitorar o sistema de resumo de sessões
"""

import streamlit as st
import json
import time
import os
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import asyncio
import html

# Configuração da página
st.set_page_config(
    page_title="🛠️ Viewer Debug - Session Summarizer",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
.debug-container {
    background-color: #1e1e1e;
    color: #ffffff;
    padding: 1rem;
    border-radius: 5px;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    max-height: 400px;
    overflow-y: auto;
    margin: 1rem 0;
}

.success-box {
    background-color: #d4edda;
    color: #155724;
    padding: 1rem;
    border-left: 4px solid #28a745;
    border-radius: 5px;
    margin: 0.5rem 0;
}

.error-box {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-left: 4px solid #dc3545;
    border-radius: 5px;
    margin: 0.5rem 0;
}

.warning-box {
    background-color: #fff3cd;
    color: #856404;
    padding: 1rem;
    border-left: 4px solid #ffc107;
    border-radius: 5px;
    margin: 0.5rem 0;
}

.info-box {
    background-color: #d1ecf1;
    color: #0c5460;
    padding: 1rem;
    border-left: 4px solid #17a2b8;
    border-radius: 5px;
    margin: 0.5rem 0;
}

.metric-card {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin: 0.5rem 0;
}
</style>
""", unsafe_allow_html=True)

# Configurações
API_URL = "http://localhost:8991"
CLAUDE_PROJECTS_PATH = Path("/home/suthub/.claude/projects")
SESSION_NAMES_FILE = Path("/home/suthub/.claude/api-claude-code-viewer/session_names.json")
PROJECT_NAMES_FILE = Path("/home/suthub/.claude/api-claude-code-viewer/project_names.json")

# ============================================================================
# 📁 SISTEMA DE ORGANIZAÇÃO DE PROJETOS
# ============================================================================

def load_project_names():
    """Carrega nomes personalizados dos projetos do arquivo JSON"""
    try:
        if PROJECT_NAMES_FILE.exists():
            with open(PROJECT_NAMES_FILE, 'r', encoding='utf-8') as f:
                names = json.load(f)
                if isinstance(names, dict):
                    return names
                else:
                    add_debug_log("warning", "Arquivo project_names.json com formato inválido")
        return {}
    except Exception as e:
        add_debug_log("error", f"Erro ao carregar nomes de projetos: {str(e)}")
        return {}

def save_project_names(names_dict):
    """Salva nomes personalizados dos projetos no arquivo JSON"""
    try:
        PROJECT_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        if not isinstance(names_dict, dict):
            raise ValueError("names_dict deve ser um dicionário")
        
        # Backup do arquivo existente
        if PROJECT_NAMES_FILE.exists():
            backup_file = PROJECT_NAMES_FILE.with_suffix('.json.backup')
            import shutil
            shutil.copy2(PROJECT_NAMES_FILE, backup_file)
        
        with open(PROJECT_NAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(names_dict, f, ensure_ascii=False, indent=2)
        
        add_debug_log("info", f"Nomes de projetos salvos: {len(names_dict)} entradas")
        return True
    except Exception as e:
        add_debug_log("error", f"Erro ao salvar nomes de projetos: {str(e)}")
        return False

def clean_project_name(directory_name):
    """Gera nome amigável automático para diretório baseado em padrões"""
    try:
        # Remover prefixos comuns
        name = directory_name
        
        # Remover "-home-suthub--claude-"
        if name.startswith("-home-suthub--claude-"):
            name = name[21:]  # Remove o prefixo
        elif name.startswith("-home-suthub--"):
            name = name[14:]  # Remove prefixo genérico
        
        # Substituir hífens por espaços e capitalizar
        name = name.replace("-", " ")
        name = name.replace("  ", " ")  # Remover espaços duplos
        
        # Capitalizar palavras importantes
        words = name.split()
        cleaned_words = []
        for word in words:
            if word.lower() in ['api', 'sdk', 'app', 'code', 'chat', 'claude', 'viewer']:
                cleaned_words.append(word.upper())
            else:
                cleaned_words.append(word.capitalize())
        
        result = " ".join(cleaned_words)
        
        # Casos especiais
        result = result.replace("Api", "API").replace("Sdk", "SDK").replace("App", "APP")
        
        return result if result else directory_name
        
    except Exception:
        return directory_name  # Fallback seguro

def get_project_display_name(directory_name, custom_names=None):
    """Obtém nome de exibição do projeto (personalizado ou limpo)"""
    if custom_names is None:
        custom_names = load_project_names()
    
    if directory_name in custom_names:
        custom_name = custom_names[directory_name]
        return f"📁 {custom_name}"
    
    # Usar limpeza automática como fallback
    clean_name = clean_project_name(directory_name)
    return f"📂 {clean_name}"

def set_project_custom_name(directory_name, custom_name):
    """Define nome personalizado para um projeto"""
    try:
        # Validar nome (usando mesma validação de sessões)
        is_valid, result = validate_session_name(custom_name)
        if not is_valid:
            return False, result
        
        clean_name = result
        
        # Carregar nomes existentes
        names = load_project_names()
        
        # Verificar se nome já existe para outro projeto
        for dirname, name in names.items():
            if dirname != directory_name and name.lower() == clean_name.lower():
                return False, f"Nome '{clean_name}' já usado por outro projeto"
        
        # Atualizar ou adicionar nome
        names[directory_name] = clean_name
        
        # Salvar
        if save_project_names(names):
            add_debug_log("info", f"Nome de projeto definido: {directory_name} -> '{clean_name}'")
            return True, clean_name
        else:
            return False, "Erro ao salvar nome do projeto"
            
    except Exception as e:
        add_debug_log("error", f"Erro ao definir nome do projeto: {str(e)}")
        return False, f"Erro interno: {str(e)}"

# ============================================================================
# 🏷️ SISTEMA DE NOMES PERSONALIZADOS PARA SESSÕES
# ============================================================================

def load_session_names():
    """Carrega nomes personalizados das sessões do arquivo JSON"""
    try:
        if SESSION_NAMES_FILE.exists():
            with open(SESSION_NAMES_FILE, 'r', encoding='utf-8') as f:
                names = json.load(f)
                # Validar estrutura do arquivo
                if isinstance(names, dict):
                    return names
                else:
                    add_debug_log("warning", "Arquivo session_names.json com formato inválido, criando novo")
        return {}
    except Exception as e:
        add_debug_log("error", f"Erro ao carregar nomes de sessões: {str(e)}")
        return {}

def save_session_names(names_dict):
    """Salva nomes personalizados das sessões no arquivo JSON"""
    try:
        # Criar diretório pai se não existir
        SESSION_NAMES_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Validar dados antes de salvar
        if not isinstance(names_dict, dict):
            raise ValueError("names_dict deve ser um dicionário")
        
        # Backup do arquivo existente
        if SESSION_NAMES_FILE.exists():
            backup_file = SESSION_NAMES_FILE.with_suffix('.json.backup')
            import shutil
            shutil.copy2(SESSION_NAMES_FILE, backup_file)
        
        # Salvar com indentação para legibilidade
        with open(SESSION_NAMES_FILE, 'w', encoding='utf-8') as f:
            json.dump(names_dict, f, ensure_ascii=False, indent=2)
        
        add_debug_log("info", f"Nomes de sessões salvos: {len(names_dict)} entradas")
        return True
    except Exception as e:
        add_debug_log("error", f"Erro ao salvar nomes de sessões: {str(e)}")
        return False

def validate_session_name(name):
    """Valida nome de sessão para garantir segurança e compatibilidade"""
    if not name or not isinstance(name, str):
        return False, "Nome deve ser uma string não vazia"
    
    # Limpar espaços em branco
    name = name.strip()
    
    if len(name) == 0:
        return False, "Nome não pode estar vazio"
    
    if len(name) > 100:
        return False, "Nome muito longo (máximo 100 caracteres)"
    
    # Caracteres proibidos (que podem causar problemas)
    forbidden_chars = ['<', '>', '"', "'", '&', '\\', '/', '|', ':', '*', '?']
    for char in forbidden_chars:
        if char in name:
            return False, f"Caractere '{char}' não permitido"
    
    # Nomes reservados
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 
                     'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                     'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
    if name.upper() in reserved_names:
        return False, "Nome reservado do sistema"
    
    return True, name.strip()

def get_session_display_name(session_id, custom_names=None):
    """Obtém nome de exibição da sessão (personalizado ou UUID)"""
    if custom_names is None:
        custom_names = load_session_names()
    
    if session_id in custom_names:
        custom_name = custom_names[session_id]
        # Adicionar indicador visual de nome personalizado
        return f"🏷️ {custom_name}"
    
    # Mostrar UUID truncado para melhor UX
    return f"📋 {session_id[:8]}...{session_id[-4:]}"

def set_session_custom_name(session_id, custom_name):
    """Define nome personalizado para uma sessão"""
    try:
        # Validar nome
        is_valid, result = validate_session_name(custom_name)
        if not is_valid:
            return False, result
        
        clean_name = result
        
        # Carregar nomes existentes
        names = load_session_names()
        
        # Verificar se nome já existe para outra sessão
        for sid, name in names.items():
            if sid != session_id and name.lower() == clean_name.lower():
                return False, f"Nome '{clean_name}' já usado por outra sessão"
        
        # Atualizar ou adicionar nome
        names[session_id] = clean_name
        
        # Salvar
        if save_session_names(names):
            add_debug_log("info", f"Nome personalizado definido: {session_id[:8]} -> '{clean_name}'")
            return True, clean_name
        else:
            return False, "Erro ao salvar nome personalizado"
            
    except Exception as e:
        add_debug_log("error", f"Erro ao definir nome personalizado: {str(e)}")
        return False, f"Erro interno: {str(e)}"

def remove_session_custom_name(session_id):
    """Remove nome personalizado de uma sessão"""
    try:
        names = load_session_names()
        
        if session_id in names:
            old_name = names.pop(session_id)
            if save_session_names(names):
                add_debug_log("info", f"Nome personalizado removido: {session_id[:8]} (era '{old_name}')")
                return True, f"Nome '{old_name}' removido"
            else:
                return False, "Erro ao salvar alterações"
        else:
            return True, "Sessão já usa nome padrão"
            
    except Exception as e:
        add_debug_log("error", f"Erro ao remover nome personalizado: {str(e)}")
        return False, f"Erro interno: {str(e)}"

def cleanup_orphaned_session_names():
    """Remove nomes de sessões que não existem mais (CRUD - limpeza automática)"""
    try:
        session_names = load_session_names()
        
        if not session_names:
            return 0, []  # Nenhuma limpeza necessária
        
        # Obter lista de sessões reais que existem
        existing_sessions = set()
        if CLAUDE_PROJECTS_PATH.exists():
            for project_dir in CLAUDE_PROJECTS_PATH.iterdir():
                if project_dir.is_dir():
                    for session_file in project_dir.glob("*.jsonl"):
                        existing_sessions.add(session_file.stem)
        
        # Identificar nomes órfãos
        orphaned_names = []
        cleaned_names = session_names.copy()
        
        for session_id, custom_name in session_names.items():
            if session_id not in existing_sessions:
                orphaned_names.append({
                    'session_id': session_id,
                    'custom_name': custom_name
                })
                cleaned_names.pop(session_id)
        
        # Salvar versão limpa se houve mudanças
        if orphaned_names:
            if save_session_names(cleaned_names):
                add_debug_log("info", f"Limpeza de nomes órfãos: {len(orphaned_names)} removidos", {
                    "removed_names": orphaned_names,
                    "remaining_names": len(cleaned_names)
                })
                return len(orphaned_names), orphaned_names
            else:
                add_debug_log("error", "Erro ao salvar limpeza de nomes órfãos")
                return 0, []
        
        return 0, []  # Nenhuma limpeza necessária
        
    except Exception as e:
        add_debug_log("error", f"Erro na limpeza de nomes órfãos: {str(e)}")
        return 0, []

def cleanup_orphaned_project_names():
    """Remove nomes de projetos que não existem mais (CRUD - limpeza automática)"""
    try:
        project_names = load_project_names()
        
        if not project_names:
            return 0, []
        
        # Obter lista de projetos reais que existem
        existing_projects = set()
        if CLAUDE_PROJECTS_PATH.exists():
            for project_dir in CLAUDE_PROJECTS_PATH.iterdir():
                if project_dir.is_dir():
                    existing_projects.add(project_dir.name)
        
        # Identificar nomes órfãos
        orphaned_names = []
        cleaned_names = project_names.copy()
        
        for project_dir, custom_name in project_names.items():
            if project_dir not in existing_projects:
                orphaned_names.append({
                    'project_dir': project_dir,
                    'custom_name': custom_name
                })
                cleaned_names.pop(project_dir)
        
        # Salvar versão limpa se houve mudanças
        if orphaned_names:
            if save_project_names(cleaned_names):
                add_debug_log("info", f"Limpeza de projetos órfãos: {len(orphaned_names)} removidos", {
                    "removed_projects": orphaned_names,
                    "remaining_projects": len(cleaned_names)
                })
                return len(orphaned_names), orphaned_names
            else:
                add_debug_log("error", "Erro ao salvar limpeza de projetos órfãos")
                return 0, []
        
        return 0, []
        
    except Exception as e:
        add_debug_log("error", f"Erro na limpeza de projetos órfãos: {str(e)}")
        return 0, []

def perform_full_cleanup():
    """Executa limpeza completa do sistema (CRUD - manutenção)"""
    try:
        # Limpeza de sessões órfãs
        session_cleanup_count, session_orphans = cleanup_orphaned_session_names()
        
        # Limpeza de projetos órfãos  
        project_cleanup_count, project_orphans = cleanup_orphaned_project_names()
        
        total_cleaned = session_cleanup_count + project_cleanup_count
        
        cleanup_report = {
            "total_items_cleaned": total_cleaned,
            "sessions_cleaned": session_cleanup_count,
            "projects_cleaned": project_cleanup_count,
            "session_orphans": session_orphans,
            "project_orphans": project_orphans,
            "cleanup_timestamp": datetime.now().isoformat()
        }
        
        add_debug_log("info", f"Limpeza automática executada: {total_cleaned} itens removidos", cleanup_report)
        
        return True, cleanup_report
        
    except Exception as e:
        add_debug_log("error", f"Erro na limpeza completa: {str(e)}")
        return False, {"error": str(e)}

def generate_session_name_with_claude(session_id, session_info):
    """Gera nome inteligente para sessão usando Claude Code SDK"""
    try:
        # Construir caminho do arquivo da sessão
        directory = session_info.get('directory', '')
        if not directory:
            add_debug_log("error", "Diretório da sessão não encontrado")
            return None
            
        file_path = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
        
        if not file_path.exists():
            # Tentar caminho alternativo se disponível
            alt_path = Path(session_info.get('file_path', ''))
            if alt_path.exists():
                file_path = alt_path
            else:
                add_debug_log("error", f"Arquivo de sessão não encontrado: {file_path}")
                return None
        
        # Ler mensagens da sessão
        messages = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data = json.loads(line.strip())
                        if data.get('type') == 'user':
                            content = data.get('message', {}).get('content', '')
                            if content:
                                messages.append(f"User: {content}")
                        elif data.get('type') == 'assistant':
                            content = data.get('content', '')
                            if content:
                                # Limitar tamanho para não sobrecarregar
                                messages.append(f"Assistant: {content[:500]}...")
                    except json.JSONDecodeError:
                        continue
        
        if not messages:
            add_debug_log("warning", "Nenhuma mensagem encontrada na sessão")
            return None
        
        # Criar prompt para Claude gerar nome
        conversation_sample = "\n".join(messages[:10])  # Apenas primeiras 10 mensagens
        
        prompt = f"""Baseado nesta conversa, responda APENAS com um nome descritivo de 20-40 caracteres:

{conversation_sample}

IMPORTANTE: Responda APENAS o nome, sem explicações, aspas ou formatação.

Exemplos de resposta adequada:
Implementação API REST
Debug sistema login
Configuração Docker
Análise performance

Nome:"""

        # Usar API Claude para gerar nome
        try:
            payload = {
                "content": prompt,
                "summary_type": "conciso"
            }
            
            response = requests.post(
                f"{API_URL}/api/summarize-custom",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    suggested_name = result.get('summary', '').strip()
                    
                    # Extrair nome da resposta do Claude - versão melhorada
                    import re
                    
                    # 1. Tentar encontrar nome entre aspas
                    quote_matches = re.findall(r'"([^"]{10,50})"', suggested_name)
                    if quote_matches:
                        suggested_name = quote_matches[-1]
                    
                    # 2. Se não encontrou aspas, tentar extrair da última linha não vazia
                    elif '\n' in suggested_name:
                        lines = suggested_name.split('\n')
                        for line in reversed(lines):
                            line = line.strip()
                            if line and len(line) <= 50 and not line.startswith('**') and not line.startswith('Nome'):
                                suggested_name = line
                                break
                    
                    # 3. Se é uma resposta curta direta, usar ela mesma
                    elif len(suggested_name) <= 50:
                        pass  # Manter como está
                    
                    # 4. Se é muito longa, tentar extrair do início
                    else:
                        # Pegar primeira frase válida
                        sentences = suggested_name.split('.')
                        for sentence in sentences:
                            clean_sentence = sentence.strip()
                            if 10 <= len(clean_sentence) <= 50:
                                suggested_name = clean_sentence
                                break
                    
                    # Limpar caracteres problemáticos
                    suggested_name = suggested_name.strip('"\'*-• ').replace('**', '').replace('Nome:', '').strip()
                    
                    # Debug: mostrar nome extraído
                    add_debug_log("debug", f"Nome extraído da resposta: '{suggested_name}'")
                    
                    # Validar nome gerado
                    is_valid, clean_name = validate_session_name(suggested_name)
                    if is_valid and len(clean_name) <= 50:
                        add_debug_log("info", f"Nome gerado por IA: '{clean_name}' para sessão {session_id[:8]}")
                        return clean_name
                    else:
                        add_debug_log("warning", f"Nome gerado inválido: '{suggested_name}' - Motivo: {clean_name}")
                        # Tentar usar uma versão simplificada
                        simple_name = suggested_name[:40].strip()
                        is_simple_valid, simple_clean = validate_session_name(simple_name)
                        if is_simple_valid:
                            add_debug_log("info", f"Usando nome simplificado: '{simple_clean}'")
                            return simple_clean
                        return None
                        
                else:
                    add_debug_log("error", f"Erro na API: {result.get('error', 'Desconhecido')}")
                    return None
            else:
                add_debug_log("error", f"Erro HTTP na geração de nome: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            add_debug_log("error", f"Erro de conexão ao gerar nome: {str(e)}")
            return None
            
    except Exception as e:
        add_debug_log("error", f"Erro ao gerar nome com Claude: {str(e)}")
        return None

# ============================================================================

def sanitize_html_text(text):
    """Sanitiza texto para evitar problemas de renderização HTML"""
    if not text:
        return ""
    # Escapar caracteres HTML perigosos
    text = html.escape(str(text))
    # Remover caracteres de controle que podem causar problemas
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return text

# Estado da sessão
if "debug_logs" not in st.session_state:
    st.session_state.debug_logs = []
if "test_results" not in st.session_state:
    st.session_state.test_results = {}
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None
if "debug_mode" not in st.session_state:
    st.session_state.debug_mode = True  # Ativado por padrão

def add_debug_log(level: str, message: str, details: dict = None):
    """Adiciona log de debug com melhor rastreamento"""
    import traceback
    import inspect
    
    # Só registra logs se modo debug estiver ativo OU for um erro
    if not st.session_state.get('debug_mode', False) and level.upper() != "ERROR":
        return
    
    # Capturar informação do contexto
    caller_info = {}
    try:
        frame = inspect.currentframe().f_back
        caller_info = {
            "function": frame.f_code.co_name,
            "line": frame.f_lineno,
            "file": frame.f_code.co_filename.split('/')[-1]
        }
    except:
        caller_info = {"function": "unknown", "line": 0, "file": "unknown"}
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "details": details or {},
        "caller": caller_info,
        "stack_trace": traceback.format_stack()[-3:-1] if level.upper() == "ERROR" else None
    }
    st.session_state.debug_logs.append(log_entry)
    
    # Manter apenas os últimos 500 logs (aumentado para melhor debug)
    if len(st.session_state.debug_logs) > 500:
        st.session_state.debug_logs = st.session_state.debug_logs[-500:]

def test_viewer_connection():
    """Testa acesso direto aos arquivos de sessão"""
    try:
        sessions = get_available_sessions_direct()
        add_debug_log("info", f"Acesso direto - {len(sessions)} sessões encontradas")
        return True, len(sessions)
    except Exception as e:
        add_debug_log("error", f"Erro no acesso direto: {str(e)}")
        return False, 0

def get_available_sessions_direct():
    """Obtém lista de sessões diretamente do filesystem"""
    sessions = []
    try:
        if not CLAUDE_PROJECTS_PATH.exists():
            add_debug_log("warning", f"Diretório não encontrado: {CLAUDE_PROJECTS_PATH}")
            return sessions
        
        for project_dir in CLAUDE_PROJECTS_PATH.iterdir():
            if not project_dir.is_dir():
                continue
                
            for session_file in project_dir.glob("*.jsonl"):
                try:
                    # Ler primeira e última linha para obter metadados
                    lines = []
                    with open(session_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                lines.append(json.loads(line.strip()))
                    
                    if lines:
                        first_msg = lines[0]
                        last_msg = lines[-1]
                        
                        sessions.append({
                            'session_id': session_file.stem,
                            'directory': project_dir.name,
                            'message_count': len(lines),
                            'first_interaction': first_msg.get('timestamp', 'N/A'),
                            'last_interaction': last_msg.get('timestamp', 'N/A'),
                            'file_path': str(session_file)
                        })
                except Exception as e:
                    add_debug_log("error", f"Erro ao processar {session_file}: {str(e)}")
                    
        # Ordenar por último timestamp
        sessions.sort(key=lambda x: x['last_interaction'], reverse=True)
        return sessions
        
    except Exception as e:
        add_debug_log("error", f"Erro ao listar sessões: {str(e)}")
        return sessions

def get_available_sessions():
    """Obtém lista de sessões disponíveis via acesso direto com limpeza automática"""
    # Executar limpeza automática a cada carregamento (CRUD)
    try:
        cleanup_count, orphans = cleanup_orphaned_session_names()
        if cleanup_count > 0:
            add_debug_log("info", f"Limpeza automática: {cleanup_count} nomes órfãos removidos")
    except Exception as e:
        add_debug_log("warning", f"Erro na limpeza automática: {str(e)}")
    
    return get_available_sessions_direct()

def get_session_details_direct(directory: str, session_id: str):
    """Obtém detalhes de uma sessão específica diretamente do arquivo"""
    try:
        session_file = CLAUDE_PROJECTS_PATH / directory / f"{session_id}.jsonl"
        
        if not session_file.exists():
            add_debug_log("error", f"Arquivo de sessão não encontrado: {session_file}")
            return None
            
        messages = []
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        message = json.loads(line.strip())
                        messages.append(message)
                    except json.JSONDecodeError as e:
                        add_debug_log("warning", f"Linha inválida em {session_file}: {e}")
        
        if messages:
            return {
                'session_id': session_id,
                'directory': directory,
                'messages': messages,
                'message_count': len(messages),
                'first_interaction': messages[0].get('timestamp', 'N/A'),
                'last_interaction': messages[-1].get('timestamp', 'N/A')
            }
        return None
        
    except Exception as e:
        add_debug_log("error", f"Erro ao ler sessão {session_id}: {str(e)}")
        return None

def test_summarizer_with_custom_content(custom_content: str, summary_type: str = "conciso"):
    """Testa resumo com conteúdo customizado"""
    execution_time = 0
    try:
        add_debug_log("info", f"Iniciando teste com conteúdo customizado", {
            "content_length": len(custom_content),
            "summary_type": summary_type
        })
        
        # Criar prompt personalizado diretamente
        base_instruction = "Analise esta conversa e crie um resumo estruturado em português brasileiro."
        
        if summary_type == "conciso":
            format_instruction = """
Formato CONCISO (máximo 20 palavras apenas):
📋 **Contexto**: [tipo de projeto/problema]
🎯 **Objetivo**: [o que foi solicitado]
✅ **Resultado**: [o que foi implementado/resolvido]
🔧 **Tecnologias**: [principais ferramentas]

Resumo ultra-conciso em 20 palavras:"""
        elif summary_type == "detalhado":
            format_instruction = """
Formato DETALHADO (máximo 400 palavras):
📋 **Contexto Completo**: [situação e background do projeto]
🎯 **Objetivos**: [todos os goals e requisitos discutidos]
⚙️ **Implementação**: [detalhes técnicos, arquitetura, decisões]
✅ **Resultados**: [tudo que foi entregue e funcionalidades]
🔧 **Tecnologias**: [stack completo utilizado]
💡 **Insights**: [aprendizados e decisões importantes]
🔄 **Próximos Passos**: [se mencionados na conversa]

Resumo:"""
        elif summary_type == "anti-churn":
            format_instruction = """
Formato ANTI-CHURN (estratégia para retenção de cliente):
💼 **Situação do Cliente**: [contexto da solicitação de cancelamento]
🎯 **Problema Identificado**: [razões pelo cancelamento - falta de leads qualificados, baixa conversão, budget limitado]
💡 **Soluções Propostas**: [estratégias específicas para gerar leads qualificados]
📊 **Análise BANT**: [Budget, Authority, Need, Timeline - como melhorar cada aspecto]
🔧 **Plano de Ação**: [passos concretos para reverter o cancelamento]
💰 **Proposta de Valor**: [benefícios claros que justifiquem continuar o serviço]
📈 **Métricas de Sucesso**: [como medir melhoria nos resultados]

Estratégia anti-churn:"""
        else:  # bullet_points
            format_instruction = """
Formato BULLET POINTS:
🎯 **Objetivos Principais:**
• [objetivo 1]
• [objetivo 2]

⚙️ **Implementação:**
• [implementação 1]
• [implementação 2]

✅ **Resultados:**
• [resultado 1]
• [resultado 2]

🔧 **Tecnologias:**
• [tech 1]
• [tech 2]

Resumo:"""
        
        full_prompt = f"{base_instruction}\n{format_instruction}\n\nConversa para análise:\n{custom_content[:10000]}"  # Limitar a 10k chars
        
        start_time = time.time()
        
        # Fazer chamada direta ao endpoint de resumo customizado
        payload = {
            "content": custom_content,
            "summary_type": summary_type
        }
        
        try:
            response = requests.post(
                f"{API_URL}/api/summarize-custom", 
                json=payload,
                timeout=120,
                headers={"Content-Type": "application/json"}
            )
            execution_time = time.time() - start_time
            
            add_debug_log("debug", f"Resposta da API customizada recebida", {
                "status_code": response.status_code,
                "execution_time": execution_time,
                "response_size": len(response.content) if response.content else 0
            })
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    add_debug_log("info", f"Resumo customizado concluído com sucesso em {execution_time:.2f}s", {
                        "summary_length": len(result.get('summary', '')),
                        "has_summary": bool(result.get('summary')),
                        "success": result.get('success', False)
                    })
                    return True, result, execution_time
                except json.JSONDecodeError as je:
                    add_debug_log("error", f"Erro ao decodificar JSON customizado: {str(je)}")
                    return False, {"error": f"Resposta inválida: {str(je)}"}, execution_time
            else:
                error_details = {
                    "status_code": response.status_code,
                    "response_text": response.text[:1000]
                }
                add_debug_log("error", f"Erro HTTP {response.status_code} no resumo customizado", error_details)
                return False, {"error": f"HTTP {response.status_code}: {response.text}"}, execution_time
        
        except requests.exceptions.Timeout:
            add_debug_log("error", f"Timeout no resumo customizado após {execution_time:.2f}s")
            return False, {"error": f"Timeout após {execution_time:.2f}s"}, execution_time
        except requests.exceptions.ConnectionError as ce:
            add_debug_log("error", f"Erro de conexão no resumo customizado: {str(ce)}")
            return False, {"error": f"Erro de conexão: {str(ce)}"}, execution_time
        
    except Exception as e:
        add_debug_log("error", f"Erro no teste customizado: {str(e)}")
        return False, {"error": str(e)}, execution_time

def test_summarizer_endpoint(directory: str, session_id: str, summary_type: str = "conciso"):
    """Testa endpoint de resumo com debug detalhado"""
    execution_time = 0
    try:
        add_debug_log("info", f"Iniciando teste de resumo", {
            "directory": directory,
            "session_id": session_id,
            "summary_type": summary_type,
            "url": f"{API_URL}/api/summarize"
        })
        
        payload = {
            "directory": directory,
            "session_id": session_id,
            "summary_type": summary_type
        }
        
        start_time = time.time()
        
        # Teste de conectividade primeiro
        try:
            health_check = requests.get(f"{API_URL}/health", timeout=5)
            add_debug_log("debug", f"Health check: {health_check.status_code}")
        except Exception as he:
            add_debug_log("warning", f"Health check falhou: {str(he)}")
        
        response = requests.post(
            f"{API_URL}/api/summarize", 
            json=payload,
            timeout=60,
            headers={"Content-Type": "application/json"}
        )
        execution_time = time.time() - start_time
        
        add_debug_log("debug", f"Resposta recebida", {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "execution_time": execution_time,
            "response_size": len(response.content) if response.content else 0
        })
        
        if response.status_code == 200:
            try:
                result = response.json()
                add_debug_log("info", f"Resumo concluído com sucesso em {execution_time:.2f}s", {
                    "summary_length": len(result.get('summary', '')),
                    "metrics": result.get('metrics', {}),
                    "has_summary": bool(result.get('summary')),
                    "success": result.get('success', False)
                })
                return True, result, execution_time
            except json.JSONDecodeError as je:
                add_debug_log("error", f"Erro ao decodificar JSON da resposta: {str(je)}", {
                    "response_text": response.text[:500],  # Primeiros 500 chars
                    "content_type": response.headers.get('content-type')
                })
                return False, {"error": f"Resposta inválida: {str(je)}"}, execution_time
        else:
            error_details = {
                "status_code": response.status_code,
                "response_text": response.text[:1000],  # Primeiros 1000 chars
                "headers": dict(response.headers)
            }
            add_debug_log("error", f"Erro HTTP {response.status_code} no resumo", error_details)
            return False, {"error": f"HTTP {response.status_code}: {response.text}"}, execution_time
            
    except requests.exceptions.Timeout as te:
        add_debug_log("error", f"Timeout na requisição de resumo após {execution_time:.2f}s: {str(te)}")
        return False, {"error": f"Timeout após {execution_time:.2f}s"}, execution_time
    except requests.exceptions.ConnectionError as ce:
        add_debug_log("error", f"Erro de conexão no resumo: {str(ce)}", {
            "url": f"{API_URL}/api/summarize",
            "directory": directory
        })
        return False, {"error": f"Erro de conexão: {str(ce)}"}, execution_time
    except Exception as e:
        add_debug_log("error", f"Erro inesperado na requisição de resumo: {str(e)}", {
            "exception_type": type(e).__name__,
            "directory": directory,
            "session_id": session_id
        })
        return False, {"error": f"Erro inesperado: {str(e)}"}, execution_time

def main():
    """Interface principal de debug"""
    
    # Cabeçalho
    
    # Sidebar com controles
    with st.sidebar:
        st.header("🔧 Controles")
        
        # Toggle Debug Mode
        st.session_state.debug_mode = st.checkbox(
            "🔍 Modo Debug Avançado", 
            value=st.session_state.debug_mode,
            help="Ativa logs detalhados e informações técnicas avançadas"
        )
        
        st.divider()
        
        # Status da API
        st.subheader("🌟 Status da API")
        
        # Teste automático de conexão
        try:
            sessions = get_available_sessions_direct()
            st.success(f"🚀 Acesso Direto OK - {len(sessions)} sessões encontradas")
        except Exception as e:
            st.error(f"❌ Erro no Acesso Direto - {str(e)}")
        
        # Teste de conexão manual
        if st.button("🔄 Testar Novamente", key="test_again_1", use_container_width=True):
            st.rerun()
        
        st.divider()
        
        # Limpeza de logs
        if st.button("🗑️ Limpar Logs", key="clear_logs_1", use_container_width=True):
            st.session_state.debug_logs = []
            st.rerun()
        
        # Informações avançadas quando debug está ativo
        if st.session_state.debug_mode:
            st.subheader("🔍 Debug Avançado")
            
            # Estatísticas dos logs
            if st.session_state.debug_logs:
                log_levels = {}
                for log in st.session_state.debug_logs[-50:]:  # Últimos 50
                    level = log["level"].upper()
                    log_levels[level] = log_levels.get(level, 0) + 1
                
                st.json({"Logs por nível": log_levels})
            
            # Debug level
            debug_level = st.selectbox(
                "Nível de Debug",
                ["info", "warning", "error", "all"],
                index=3,  # "all" selecionado por padrão
                help="Mostra mais detalhes técnicos quando ativo"
            )
            
            st.metric("Logs em Memória", len(st.session_state.debug_logs))
            st.metric("Testes Executados", len(st.session_state.test_results))
            
            # 📁 Gerenciamento de Projetos
            st.subheader("📁 Organização de Projetos")
            
            # Listar projetos disponíveis
            if CLAUDE_PROJECTS_PATH.exists():
                available_projects = [d.name for d in CLAUDE_PROJECTS_PATH.iterdir() if d.is_dir()]
                project_custom_names = load_project_names()
                
                # Estatísticas rápidas
                st.metric("Total de Projetos", len(available_projects))
                st.metric("Projetos Renomeados", len(project_custom_names))
                
                # Seletor de projeto para renomear
                if available_projects:
                    project_to_rename = st.selectbox(
                        "Selecionar projeto para renomear:",
                        available_projects,
                        format_func=lambda x: get_project_display_name(x, project_custom_names)
                    )
                    
                    if st.button("📁 Renomear Projeto Selecionado", key="rename_project_btn", use_container_width=True):
                        st.session_state.show_project_rename_modal = True
                        st.session_state.project_to_rename = project_to_rename
                    
                    # Mostrar preview dos nomes limpos
                    with st.expander("👀 Preview dos Nomes Automáticos"):
                        for proj in available_projects[:5]:  # Mostrar apenas 5 para não sobrecarregar
                            original = proj
                            cleaned = clean_project_name(proj)
                            custom = project_custom_names.get(proj, "")
                            
                            if custom:
                                st.write(f"📁 **{custom}** (personalizado)")
                            else:
                                st.write(f"📂 **{cleaned}** (auto)")
                            st.caption(f"Original: `{original}`")
                            st.markdown("---")
            
            # 🧹 Sistema CRUD - Manutenção
            st.subheader("🧹 Manutenção do Sistema")
            
            # Estatísticas de limpeza
            session_names_count = len(load_session_names())
            project_names_count = len(load_project_names())
            
            col_stats1, col_stats2 = st.columns(2)
            with col_stats1:
                st.metric("Nomes de Sessões", session_names_count)
            with col_stats2:
                st.metric("Nomes de Projetos", project_names_count)
            
            # Botão de limpeza manual
            if st.button("🧹 Executar Limpeza Completa", key="manual_cleanup", use_container_width=True, help="Remove nomes de sessões/projetos que não existem mais"):
                with st.spinner("🧹 Executando limpeza automática..."):
                    success, report = perform_full_cleanup()
                    
                    if success:
                        total_cleaned = report['total_items_cleaned']
                        
                        if total_cleaned > 0:
                            st.success(f"✅ Limpeza concluída: {total_cleaned} itens órfãos removidos")
                            
                            # Detalhes da limpeza
                            if report['sessions_cleaned'] > 0:
                                st.info(f"🏷️ Sessões limpas: {report['sessions_cleaned']}")
                            if report['projects_cleaned'] > 0:
                                st.info(f"📁 Projetos limpos: {report['projects_cleaned']}")
                                
                            # Mostrar itens removidos
                            with st.expander("🔍 Ver Itens Removidos"):
                                if report['session_orphans']:
                                    st.write("**Sessões Órfãs Removidas:**")
                                    for orphan in report['session_orphans']:
                                        st.write(f"- `{orphan['session_id'][:8]}...` → '{orphan['custom_name']}'")
                                
                                if report['project_orphans']:
                                    st.write("**Projetos Órfãos Removidos:**")
                                    for orphan in report['project_orphans']:
                                        st.write(f"- `{orphan['project_dir']}` → '{orphan['custom_name']}'")
                                        
                            st.rerun()
                        else:
                            st.info("✅ Sistema já está limpo - nenhum item órfão encontrado")
                    else:
                        st.error(f"❌ Erro na limpeza: {report.get('error', 'Desconhecido')}")
            
            # Informações sobre limpeza automática
            st.caption("ℹ️ A limpeza automática roda toda vez que a lista de sessões é carregada")
            
            # Configurações avançadas de sessão
            st.subheader("⚙️ Config de Sessão")
            
            # System prompt personalizado
            custom_system_prompt = st.text_area(
                "System Prompt:",
                value=st.session_state.get('session_system_prompt', ''),
                height=80,
                placeholder="Ex: Você é um especialista em...",
                help="Prompt de sistema para novas sessões de chat"
            )
            st.session_state.session_system_prompt = custom_system_prompt
            
            # Ferramentas permitidas
            available_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebFetch"]
            selected_tools = st.multiselect(
                "Ferramentas:",
                available_tools,
                default=st.session_state.get('session_tools', available_tools),  # Todos selecionados por padrão
                help="Ferramentas que o Claude pode usar"
            )
            st.session_state.session_tools = selected_tools
            
            # Outras configurações
            max_turns = st.number_input("Max Turnos:", value=20, min_value=1, max_value=100)
            st.session_state.session_max_turns = max_turns
        
        st.divider()
        
        # Informações do sistema
        st.subheader("📊 Status do Sistema")
        
        # Indicadores de status em tempo real
        col_status1, col_status2, col_status3 = st.columns(3)
        
        with col_status1:
            # Contar erros recentes (últimos 10 minutos)
            recent_errors = 0
            current_time = datetime.now()
            for log in st.session_state.debug_logs[-50:]:  # Últimos 50 logs
                log_time = datetime.fromisoformat(log["timestamp"])
                if (current_time - log_time).total_seconds() < 600:  # 10 minutos
                    if log["level"].upper() == "ERROR":
                        recent_errors += 1
            
            error_status = "🔴 Erros" if recent_errors > 0 else "✅ Normal"
            st.metric("Status", error_status, delta=f"{recent_errors} erros recentes")
        
        with col_status2:
            st.metric("Logs Total", len(st.session_state.debug_logs))
        
        with col_status3:
            # Status dos últimos testes
            recent_tests = len(st.session_state.test_results) if hasattr(st.session_state, 'test_results') else 0
            success_rate = 0
            if hasattr(st.session_state, 'test_results') and st.session_state.test_results:
                successful = sum(1 for r in st.session_state.test_results.values() 
                               if r['result'].get('success', False))
                success_rate = (successful / len(st.session_state.test_results) * 100) if st.session_state.test_results else 0
            
            st.metric("Testes", recent_tests, delta=f"{success_rate:.0f}% sucesso")
        
        
        # Alertas importantes na página principal
        if recent_errors > 0:
            st.error(f"⚠️ **{recent_errors} erro(s) recente(s) detectado(s)!** Verifique a aba 'Logs de Debug' para detalhes.")
        
        # Resumo dos últimos testes falhados
        if hasattr(st.session_state, 'test_results'):
            failed_tests = [r for r in st.session_state.test_results.values() if not r.get('success', True)]
            if failed_tests:
                st.warning(f"⚠️ **{len(failed_tests)} teste(s) falharam.** Veja detalhes na aba 'Métricas'.")
            elif len(st.session_state.test_results) > 0:
                successful_tests = len([r for r in st.session_state.test_results.values() if r.get('success', True)])
                st.success(f"🎯 **{successful_tests} teste(s) executado(s) com sucesso!** Sistema funcionando perfeitamente.")
    
    # Tabs principais
    tab1, tab2, tab3 = st.tabs([
        "🧪 Testes de Resumo", 
        "📝 Logs de Debug", 
        "📊 Métricas"
    ])
    
    # Tab 1: Testes de Resumo
    with tab1:
        st.header("🧪 Testes de Funcionalidade")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Sessões Disponíveis")
            
            # Atualização automática da lista de sessões
            sessions = get_available_sessions()
            st.session_state.available_sessions = sessions
                
            if sessions:
                # Carregar nomes personalizados uma vez para performance
                session_custom_names = load_session_names()
                project_custom_names = load_project_names()
                
                # 🔍 Campo de busca melhorado
                col_search, col_clear = st.columns([4, 1])
                with col_search:
                    search_term = st.text_input(
                        "🔍 Buscar por projeto ou sessão:",
                        placeholder="Digite nome do projeto, sessão ou UUID...",
                        key="session_search"
                    )
                with col_clear:
                    if st.button("🔄 Limpar", key="clear_search", use_container_width=True):
                        st.session_state.session_search = ""
                        st.rerun()
                
                # Filtrar sessões baseado na busca melhorada
                filtered_sessions = sessions
                if search_term:
                    filtered_sessions = []
                    search_lower = search_term.lower()
                    for session in sessions:
                        session_id = session['session_id']
                        directory = session['directory']
                        
                        # Obter nomes amigáveis
                        session_friendly_name = get_session_display_name(session_id, session_custom_names)
                        project_friendly_name = get_project_display_name(directory, project_custom_names)
                        
                        # Buscar em múltiplos campos
                        if (search_lower in session_friendly_name.lower() or 
                            search_lower in project_friendly_name.lower() or
                            search_lower in session_id.lower() or 
                            search_lower in directory.lower()):
                            filtered_sessions.append(session)
                
                # Mostrar contador de resultados
                if search_term:
                    st.caption(f"📊 {len(filtered_sessions)} de {len(sessions)} sessões encontradas")
                
                # 📊 Estatísticas por projeto
                st.markdown("### 📊 Projetos")
                project_stats = {}
                for session in filtered_sessions:
                    directory = session['directory']
                    if directory not in project_stats:
                        project_stats[directory] = {
                            'count': 0,
                            'last_activity': session.get('last_interaction', 'N/A')
                        }
                    project_stats[directory]['count'] += 1
                    # Manter a atividade mais recente
                    if session.get('last_interaction', '') > project_stats[directory]['last_activity']:
                        project_stats[directory]['last_activity'] = session.get('last_interaction', 'N/A')
                
                # Exibir estatísticas em formato compacto
                stats_data = []
                for directory, stats in project_stats.items():
                    project_display = get_project_display_name(directory, project_custom_names)
                    stats_data.append({
                        "📁 Projeto": project_display,
                        "📊 Sessões": stats['count'],
                        "📅 Última Atividade": stats['last_activity'][:16] if stats['last_activity'] != 'N/A' else 'N/A'
                    })
                
                if stats_data:
                    st.dataframe(stats_data, use_container_width=True, hide_index=True)
                
                st.markdown("### 📋 Selecionar Sessão")
                
                # Agrupar sessões por projeto para melhor organização
                sessions_by_project = {}
                for session in filtered_sessions[:50]:  # Aumentar limite para 50
                    directory = session['directory']
                    if directory not in sessions_by_project:
                        sessions_by_project[directory] = []
                    sessions_by_project[directory].append(session)
                
                # Criar opções com nomes limpos
                session_options = []
                for directory, project_sessions in sessions_by_project.items():
                    # Nome limpo do projeto
                    project_display = get_project_display_name(directory, project_custom_names)
                    
                    for session in project_sessions:
                        session_id = session['session_id']
                        session_display = get_session_display_name(session_id, session_custom_names)
                        
                        # Formato otimizado: "📁 Projeto | 🏷️ Sessão"
                        display_name = f"{project_display} | {session_display}"
                        session_options.append((display_name, session))
                    
                selected_idx = st.selectbox(
                    "Selecionar Sessão:",
                    range(len(session_options)),
                    format_func=lambda i: session_options[i][0] if session_options else "Nenhuma"
                )
                    
                if session_options:
                    st.session_state.selected_session = session_options[selected_idx][1]
                    selected_session = session_options[selected_idx][1]
                    
                    # Botões de ação para a sessão selecionada
                    col_action1, col_action2, col_action3 = st.columns(3)
                    
                    with col_action1:
                        if st.button("🗑️ Deletar", key="delete_selected_session", use_container_width=True, type="secondary"):
                            # Deletar a sessão diretamente do filesystem (debug viewer)
                            try:
                                file_path = Path(selected_session.get('file_path', ''))
                                session_id = selected_session['session_id']
                                
                                if file_path.exists():
                                    # Deletar arquivo físico
                                    import os
                                    os.remove(file_path)
                                    
                                    # Remover nome personalizado se existir
                                    custom_names = load_session_names()
                                    if session_id in custom_names:
                                        old_name = custom_names.pop(session_id)
                                        save_session_names(custom_names)
                                        add_debug_log("info", f"Nome personalizado '{old_name}' removido junto com a sessão")
                                    
                                    st.success(f"✅ Sessão {session_id[:8]}... deletada permanentemente!")
                                    
                                    # Log da exclusão
                                    add_debug_log("info", "Sessão deletada (arquivo físico)", {
                                        "deleted_file": str(file_path),
                                        "deleted_session_id": session_id
                                    })
                                    
                                    # Limpar seleção atual e atualizar
                                    st.session_state.selected_session = None
                                    if 'last_generated_summary' in st.session_state:
                                        del st.session_state.last_generated_summary
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error(f"❌ Arquivo não encontrado: {file_path}")
                                    add_debug_log("error", f"Arquivo de sessão não encontrado: {file_path}")
                            
                            except Exception as e:
                                st.error(f"❌ Erro na exclusão: {str(e)}")
                                add_debug_log("error", f"Erro na exclusão da sessão: {str(e)}")
                    
                    with col_action2:
                        # 🏷️ Sistema de Renomeação de Sessão
                        session_id = selected_session['session_id']
                        
                        # Botão para abrir modal de renomeação
                        if st.button("🏷️ Renomear", key="rename_session_btn", use_container_width=True, type="primary"):
                            st.session_state.show_rename_modal = True
                            st.session_state.rename_session_id = session_id
                    
                    with col_action3:
                        if st.button("🔄 Recarregar", key="reload_session_data", use_container_width=True, type="secondary"):
                            # Forçar recarregamento dos dados da sessão
                            st.rerun()
                    
                    
                    # Carregar e exibir conteúdo da sessão para edição
                    file_path = Path(selected_session.get('file_path', ''))
                    
                    # Carregar metadados da sessão
                    if file_path.exists():
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                lines = f.readlines()
                            
                            # Extrair conversa de forma simplificada para estatísticas
                            conversation_parts = []
                            for line in lines:
                                try:
                                    data = json.loads(line.strip())
                                    if data.get('type') == 'user':
                                        message_content = data.get('message', {}).get('content', '')
                                        conversation_parts.append(f"👤 Usuário: {message_content}")
                                    elif data.get('type') == 'assistant':
                                        message = data.get('message', {})
                                        if isinstance(message.get('content'), list):
                                            # Extrair texto dos blocos de conteúdo
                                            text_parts = []
                                            for block in message['content']:
                                                if isinstance(block, dict) and block.get('type') == 'text':
                                                    text_parts.append(block.get('text', ''))
                                            content = ' '.join(text_parts)
                                        else:
                                            content = str(message.get('content', ''))
                                        conversation_parts.append(f"🤖 Claude: {content}")
                                except json.JSONDecodeError:
                                    continue
                            
                            full_conversation = '\n\n'.join(conversation_parts)
                            
                            # Armazenar conversa original para uso posterior
                            st.session_state.original_conversation = full_conversation
                            
                            # Informações sobre a sessão
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.info(f"📊 {len(conversation_parts)} mensagens")
                            with col_info2:
                                st.info(f"📝 {len(full_conversation):,} caracteres")
                            
                        except Exception as e:
                            st.error(f"❌ Erro ao ler arquivo: {str(e)}")
                    else:
                        st.error(f"❌ Arquivo não encontrado: {file_path}")
                            
                    # Área de Resumo Gerado com UI/UX melhorada
                    if 'last_generated_summary' in st.session_state:
                        summary_data = st.session_state.last_generated_summary
                        is_success = summary_data.get('success', False)
                        
                        if is_success:
                                # Apenas o conteúdo, sem headers ou informações extras
                                
                                # Área de texto com melhor formatação
                                summary_content = summary_data.get('result', {}).get('summary', 'N/A')
                                
                                # Parser de markdown melhorado para resumos
                                import re
                                
                                def parse_summary_markdown(content: str) -> str:
                                    """Parser robusto para formatação de resumos"""
                                    # Sanitizar conteúdo primeiro
                                    if not content:
                                        return ""
                                    # Remover caracteres de controle problemáticos mas manter quebras de linha
                                    html = ''.join(char for char in str(content) if ord(char) >= 32 or char in '\n\t\r')
                                    
                                    # Headers (## título)
                                    html = re.sub('^## (.*?)$', 
                                                 '<h3 style="color: #667eea; margin: 25px 0 15px 0; font-weight: bold; font-size: 18px; border-bottom: 2px solid #f0f0f0; padding-bottom: 8px;">\\1</h3>', 
                                                 html, flags=re.MULTILINE)
                                    
                                    # Bold com emojis (📋 **texto**)
                                    html = re.sub('(📋|🎯|✅|🔧|⚙️|💡|🔄)\\s*\\*\\*(.*?)\\*\\*:', 
                                                 '<div style="margin: 15px 0;"><span style="font-size: 16px; margin-right: 10px;">\\1</span><strong style="color: #333; font-size: 15px;">\\2:</strong></div>', 
                                                 html)
                                    
                                    # Bold simples
                                    html = re.sub('\\*\\*(.*?)\\*\\*', '<strong style="color: #333;">\\1</strong>', html)
                                    
                                    # Separadores horizontais
                                    html = re.sub('^---$', '<hr style="border: none; border-top: 2px solid #e9ecef; margin: 25px 0;">', html, flags=re.MULTILINE)
                                    
                                    # Listas com bullet points (• item)
                                    html = re.sub('^• (.*?)$', '<div style="margin: 8px 0 8px 20px; color: #555;"><span style="color: #667eea; margin-right: 8px;">•</span>\\1</div>', html, flags=re.MULTILINE)
                                    
                                    # Código inline (`código`)
                                    html = re.sub('`(.*?)`', '<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #e83e8c;">\\1</code>', html)
                                    
                                    # Emojis isolados com espaçamento
                                    html = re.sub('^(📋|🎯|✅|🔧|⚙️|💡|🔄|📊|💰)', '<span style="display: inline-block; margin-right: 8px; font-size: 16px;">\\1</span>', html, flags=re.MULTILINE)
                                    
                                    # Quebras de linha duplas para parágrafos
                                    html = re.sub('\\n\\s*\\n', '</p><p style="margin: 15px 0; line-height: 1.6;">', html)
                                    
                                    # Quebras simples
                                    html = html.replace('\n', '<br>')
                                    
                                    # Envolver em parágrafo se não começar com tag
                                    if not html.strip().startswith('<'):
                                        html = f'<p style="margin: 15px 0; line-height: 1.6;">{html}</p>'
                                    
                                    return html
                                
                                # Aplicar parser melhorado
                                html_content = parse_summary_markdown(summary_content)
                                
                                # Mostrar apenas o conteúdo limpo
                                st.markdown(f"""
                                <div style="background: #ffffff; border: 2px solid #e9ecef; border-radius: 12px; 
                                            padding: 25px; margin: 15px 0; font-family: 'Segoe UI', Arial, sans-serif;
                                            line-height: 1.8; color: #212529; font-size: 15px;
                                            box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                                    {html_content}
                                </div>
                                """, unsafe_allow_html=True)
                                
                                # Botões de ação para sucesso
                                col_action1, col_action2, col_action3 = st.columns(3)
                                
                                with col_action1:
                                    if st.button("📋 Copiar Conteúdo", key="copy_improved", use_container_width=True):
                                        st.success("✅ Use Ctrl+A e Ctrl+C na área de texto acima")
                                
                                with col_action2:
                                    if st.button("🗑️ Deletar Sessão", key="delete_session", use_container_width=True):
                                        # Deletar permanentemente a nova sessão criada
                                        created_session = summary_data.get('new_session_created')
                                        
                                        if created_session:
                                            try:
                                                # Deletar arquivo físico diretamente
                                                session_file = CLAUDE_PROJECTS_PATH / created_session['directory'] / f"{created_session['session_id']}.jsonl"
                                                
                                                if session_file.exists():
                                                    import os
                                                    os.remove(session_file)
                                                    
                                                    # Remover nome personalizado se existir
                                                    custom_names = load_session_names()
                                                    session_id = created_session['session_id']
                                                    if session_id in custom_names:
                                                        old_name = custom_names.pop(session_id)
                                                        save_session_names(custom_names)
                                                    
                                                    st.success(f"✅ Sessão {session_id[:8]}... deletada permanentemente!")
                                                    
                                                    # Log da exclusão
                                                    add_debug_log("info", "Sessão criada foi deletada (arquivo físico)", {
                                                        "deleted_file": str(session_file),
                                                        "deleted_session_id": session_id
                                                    })
                                                    
                                                    # Remover da visualização
                                                    del st.session_state.last_generated_summary
                                                    st.rerun()
                                                else:
                                                    st.error(f"❌ Arquivo não encontrado: {session_file}")
                                                    add_debug_log("error", f"Arquivo de sessão não encontrado: {session_file}")
                                            
                                            except Exception as e:
                                                st.error(f"❌ Erro na exclusão: {str(e)}")
                                                add_debug_log("error", f"Erro na exclusão da sessão: {str(e)}")
                                        else:
                                            st.warning("⚠️ Nenhuma nova sessão para deletar")
                                            # Apenas remover da visualização se não há sessão para deletar
                                            del st.session_state.last_generated_summary
                                            st.rerun()
                                
                                with col_action3:
                                    if st.button("🔗 Nova Conversa", key="show_new_conversation", use_container_width=True):
                                        # Usar a sessão específica criada durante esta geração
                                        created_session = summary_data.get('new_session_created')
                                        
                                        if created_session:
                                            new_conversation_url = f"http://localhost:3041/{created_session['directory']}/{created_session['session_id']}"
                                            
                                            st.markdown(f"""
                                            **🔗 Nova Conversa Criada por Esta Geração:**
                                            
                                            [{new_conversation_url}]({new_conversation_url})
                                            """)
                                            st.info(f"📍 **Diretório:** `{created_session['directory']}`")
                                            st.info(f"🆔 **ID:** `{created_session['session_id']}`")
                                            st.success("🎯 **Esta é a sessão exata criada durante a geração do resumo!**")
                                            
                                            # Log da nova conversa específica
                                            add_debug_log("info", "Exibindo nova conversa específica", {
                                                "specific_directory": created_session['directory'],
                                                "specific_session_id": created_session['session_id'],
                                                "conversation_url": new_conversation_url
                                            })
                                        else:
                                            st.warning("⚠️ Nenhuma nova sessão foi detectada durante esta geração")
                                            st.info("💡 Isso pode acontecer se a geração não criou uma nova conversa ou se houve erro na detecção")
                            
                        else:
                            # Card de erro
                            st.markdown(f"""
                                <div style="background: #f8d7da; border-radius: 15px; padding: 25px; 
                                            box-shadow: 0 8px 25px rgba(0,0,0,0.1); border-left: 5px solid #dc3545; margin: 20px 0;">
                                    <div style="color: #721c24;">
                                        <h4 style="margin: 0 0 15px 0; display: flex; align-items: center;">
                                            <span style="margin-right: 8px;">⚠️</span>
                                            Erro na Geração do Resumo
                                        </h4>
                                        <div style="background: white; padding: 15px; border-radius: 8px; color: #333;">
                                            <strong>Detalhes:</strong> {sanitize_html_text(summary_data.get('error', 'Erro desconhecido'))}<br>
                                            <small><strong>Tempo:</strong> {summary_data.get('execution_time', 0):.2f}s</small>
                                        </div>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            # Botões de ação também para erros
                            col_error1, col_error2 = st.columns(2)
                            
                            with col_error1:
                                if st.button("🔗 Ver Nova Conversa", key="show_new_conversation_error", use_container_width=True):
                                    created_session = summary_data.get('new_session_created')
                                    
                                    if created_session:
                                        new_conversation_url = f"http://localhost:3041/{created_session['directory']}/{created_session['session_id']}"
                                        
                                        st.markdown(f"""
                                        **🔗 Nova Conversa (mesmo com erro):**
                                        
                                        [{new_conversation_url}]({new_conversation_url})
                                        """)
                                        st.info(f"📍 **Diretório:** `{created_session['directory']}`")
                                        st.info(f"🆔 **ID:** `{created_session['session_id']}`")
                                        st.info("💡 **Uma nova sessão foi criada mesmo com o erro**")
                                    else:
                                        st.warning("⚠️ Nenhuma nova sessão foi criada durante este erro")
                            
                            with col_error2:
                                if st.button("🗑️ Limpar Erro", key="clear_error", use_container_width=True):
                                    del st.session_state.last_generated_summary
                                    st.success("✅ Erro removido da visualização!")
                                    st.rerun()
                            
                        
                else:
                    st.warning("⚠️ Nenhuma sessão encontrada")
            else:
                st.info("📋 Clique em 'Atualizar Lista' para carregar sessões")
        
        with col2:
            st.subheader("🎯 Teste de Resumo")
            
            if st.session_state.selected_session:
                session = st.session_state.selected_session
                
                summary_type = st.selectbox(
                    "Tipos:",
                    ["conciso", "bullet_points", "detalhado", "anti-churn"],  # conciso em primeiro
                    help="Escolha o formato de resumo desejado"
                )
                
                # Explicação dos tipos
                if summary_type == "conciso":
                    st.info("📋 **Conciso**: Resumo estruturado em até 20 palavras apenas com contexto, objetivo, resultado e tecnologias")
                elif summary_type == "bullet_points":
                    st.info("🔸 **Bullet Points**: Lista organizada por tópicos com pontos principais da conversa")
                elif summary_type == "detalhado":
                    st.info("📖 **Detalhado**: Análise completa em até 400 palavras incluindo implementação, insights e próximos passos")
                else:  # anti-churn
                    st.info("💼 **Anti-Churn**: Estratégia para retenção de cliente com soluções para gerar leads qualificados e reverter cancelamento")
                
                if st.button("🚀 Executar Teste de Resumo", key="exec_test_1", use_container_width=True):
                    # Capturar lista de sessões ANTES da geração
                    sessions_before = []
                    try:
                        sessions_before = [s['session_id'] for s in get_available_sessions_direct()]
                    except:
                        sessions_before = []
                    
                    # Verificar se há conversa original e prompt customizado
                    has_conversation = hasattr(st.session_state, 'original_conversation') and st.session_state.original_conversation
                    has_custom_prompt = st.session_state.get('custom_system_prompt', '').strip()
                    use_enhanced_mode = has_conversation and has_custom_prompt
                    
                    # Log início do teste
                    add_debug_log("info", f"Iniciando teste de resumo tipo '{summary_type}'", {
                        "session_id": session['session_id'],
                        "directory": session['directory'],
                        "summary_type": summary_type,
                        "has_custom_prompt": bool(has_custom_prompt),
                        "enhanced_mode": use_enhanced_mode,
                        "sessions_before_count": len(sessions_before)
                    })
                    
                    with st.spinner("🤖 Gerando resumo..."):
                        if use_enhanced_mode:
                            # Combinar prompt customizado com conversa
                            enhanced_content = f"""INSTRUÇÕES ESPECÍFICAS: {has_custom_prompt}

CONVERSA PARA ANÁLISE:
{st.session_state.original_conversation}"""
                            
                            success, result, exec_time = test_summarizer_with_custom_content(
                                enhanced_content,
                                summary_type
                            )
                        elif has_conversation:
                            # Usar conversa original sem prompt customizado
                            success, result, exec_time = test_summarizer_with_custom_content(
                                st.session_state.original_conversation,
                                summary_type
                            )
                        else:
                            # Usar método original (fallback)
                            success, result, exec_time = test_summarizer_endpoint(
                                session['directory'], 
                                session['session_id'],
                                summary_type
                            )
                        
                        # Capturar lista de sessões APÓS a geração para detectar nova sessão
                        new_session_created = None
                        try:
                            sessions_after = get_available_sessions_direct()
                            sessions_after_ids = [s['session_id'] for s in sessions_after]
                            
                            # Encontrar nova sessão criada
                            new_session_ids = set(sessions_after_ids) - set(sessions_before)
                            if new_session_ids:
                                new_session_id = list(new_session_ids)[0]
                                new_session_created = next(s for s in sessions_after if s['session_id'] == new_session_id)
                                
                                add_debug_log("info", f"Nova sessão detectada: {new_session_id}", {
                                    "new_session": new_session_created,
                                    "sessions_before": len(sessions_before),
                                    "sessions_after": len(sessions_after)
                                })
                        except Exception as e:
                            add_debug_log("warning", f"Erro ao detectar nova sessão: {str(e)}")
                    
                    if success:
                        # Mensagem de sucesso personalizada
                        if use_enhanced_mode:
                            st.success(f"✅ Resumo gerado com prompt personalizado em {exec_time:.2f}s")
                            st.info("🎯 **Prompt aplicado:** Suas instruções específicas foram incluídas na análise")
                        else:
                            st.success(f"✅ Resumo gerado em {exec_time:.2f}s")
                        
                        # Log sucesso
                        add_debug_log("info", f"Teste concluído com sucesso em {exec_time:.2f}s", {
                            "execution_time": exec_time,
                            "summary_length": len(result.get('summary', '')),
                            "tokens_used": result.get('metrics', {}).get('input_tokens', 0) + result.get('metrics', {}).get('output_tokens', 0),
                            "used_custom_prompt": use_enhanced_mode
                        })
                        
                        
                        # Métricas
                        metrics = result.get('metrics', {})
                        col_a, col_b, col_c = st.columns(3)
                        
                        with col_a:
                            st.metric("Tokens In", metrics.get('input_tokens', 0))
                        with col_b:
                            st.metric("Tokens Out", metrics.get('output_tokens', 0))
                        with col_c:
                            st.metric("Custo", f"USD {metrics.get('cost', 0):.6f}")
                        
                        # Salva resultado para análise (incluindo prompt customizado e nova sessão)
                        test_result = {
                            "timestamp": datetime.now().isoformat(),
                            "session": session,
                            "result": result,
                            "execution_time": exec_time,
                            "summary_type": summary_type,
                            "success": True,
                            "custom_prompt": st.session_state.get('custom_system_prompt', '') if use_enhanced_mode else None,
                            "new_session_created": new_session_created  # A sessão específica criada por esta geração
                        }
                        
                        # Chave única incluindo prompt se houver
                        result_key = f"{session['session_id']}_{summary_type}"
                        if use_enhanced_mode:
                            result_key += f"_custom_{hash(has_custom_prompt) % 10000}"
                        
                        st.session_state.test_results[result_key] = test_result
                        
                        # Salvar resumo para exibição na UI melhorada
                        st.session_state.last_generated_summary = test_result
                        
                        # Forçar atualização da interface para mostrar o resumo automaticamente
                        st.rerun()
                    else:
                        error_msg = result.get('error', 'Erro desconhecido')
                        st.error(f"❌ Erro no resumo: {error_msg}")
                        
                        # Log detalhado do erro
                        add_debug_log("error", f"Falha no teste de resumo: {error_msg}", {
                            "session_id": session['session_id'],
                            "directory": session['directory'],
                            "summary_type": summary_type,
                            "execution_time": exec_time,
                            "error_details": result
                        })
                        
                        # Salva resultado do erro para análise (incluindo nova sessão se criada)
                        test_result = {
                            "timestamp": datetime.now().isoformat(),
                            "session": session,
                            "result": result,
                            "execution_time": exec_time,
                            "summary_type": summary_type,
                            "success": False,
                            "error": error_msg,
                            "new_session_created": new_session_created  # Mesmo em erro pode ter criado sessão
                        }
                        st.session_state.test_results[f"{session['session_id']}_{summary_type}"] = test_result
                        
                        # Salvar erro para exibição na UI
                        st.session_state.last_generated_summary = test_result
                        
                        # Forçar atualização da interface para mostrar o erro automaticamente
                        st.rerun()
            else:
                st.info("📋 Selecione uma sessão para testar")
    
    # Tab 2: Logs de Debug
    with tab2:
        st.header("📝 Logs de Debug")
        
        if not st.session_state.debug_mode:
            st.info("🔍 **Modo Debug Desativado** - Ative na sidebar para ver logs detalhados. Apenas erros são registrados.")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            max_logs = st.number_input("Máximo de logs:", value=50, min_value=10, max_value=200)
        with col2:
            reverse_order = st.checkbox("Mais recentes primeiro", value=True)
        with col3:
            if st.session_state.debug_mode:
                st.success("🔍 Debug Ativo")
            else:
                st.warning("⚠️ Debug Inativo")
        
        # Exibe logs
        if st.session_state.debug_logs:
            filtered_logs = st.session_state.debug_logs[-max_logs:]
            
            if not reverse_order:
                filtered_logs = list(reversed(filtered_logs))
            
            # Agrupar logs em linhas de 2 colunas (como nos testes)
            for i in range(0, len(filtered_logs), 2):
                cols = st.columns(2)
                
                for j, col in enumerate(cols):
                    if i + j < len(filtered_logs):
                        log = filtered_logs[i + j]
                        timestamp = log["timestamp"].split("T")[1][:8]
                        level = log["level"].upper()
                        message = log["message"]
                        
                        # Escolher emoji e cor baseado no level
                        if level == "ERROR":
                            emoji = "🔴"
                            color = "#fee"
                            border_color = "#f66"
                        elif level == "WARNING":
                            emoji = "🟡"
                            color = "#ffeaa7"
                            border_color = "#fdcb6e"
                        else:
                            emoji = "🔵"
                            color = "#e3f2fd"
                            border_color = "#2196f3"
                        
                        with col:
                            # Container estilizado como os testes
                            debug_info = ""
                            if st.session_state.debug_mode:
                                caller = log.get("caller", {})
                                debug_info = f"""
                                <div style="color: #666; font-size: 12px; margin-top: 5px;">
                                    📍 {caller.get('file', 'unknown')}:{caller.get('line', 0)} → {caller.get('function', 'unknown')}()
                                </div>
                                """
                            
                            st.markdown(f"""
                            <div style="border: 2px solid {border_color}; border-radius: 10px; 
                                        padding: 15px; margin: 10px 0; background: {color};">
                                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                                    <span style="font-size: 20px; margin-right: 8px;">{emoji}</span>
                                    <strong style="color: #333;">[{timestamp}] {level}</strong>
                                </div>
                                <div style="color: #555; font-size: 14px; margin-bottom: 10px;">
                                    {message}
                                </div>
                                {debug_info}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Detalhes expandidos dentro do card
                            if log.get("details"):
                                with st.expander(f"🔍 Detalhes ({timestamp})"):
                                    st.json(log["details"])
                                    
                            # Stack trace para erros (só no modo debug)
                            if st.session_state.debug_mode and log.get("stack_trace"):
                                with st.expander(f"📚 Stack Trace ({timestamp})", expanded=False):
                                    for line in log["stack_trace"]:
                                        st.code(line.strip(), language="python")
        else:
            st.info("📋 Nenhum log de debug disponível")
    
    # Tab 3: Métricas
    with tab3:
        st.header("📊 Métricas de Performance")
        
        if st.session_state.test_results:
            st.subheader("📈 Resumo dos Testes")
            
            # Métricas gerais
            total_tests = len(st.session_state.test_results)
            successful_tests = sum(1 for result in st.session_state.test_results.values() 
                                 if result['result'].get('success', False))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total de Testes", total_tests)
            with col2:
                st.metric("Sucessos", successful_tests)
            with col3:
                success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
                st.metric("Taxa de Sucesso", f"{success_rate:.1f}%")
            
            # Separar sucessos e falhas
            successful_results = [r for r in st.session_state.test_results.values() if r.get('success', True)]
            failed_results = [r for r in st.session_state.test_results.values() if not r.get('success', True)]
            
            # Mostrar falhas primeiro se houver
            if failed_results:
                st.subheader("❌ Testes Falhados")
                
                for test_result in failed_results:
                    session = test_result['session']
                    
                    # Card de erro
                    st.markdown(f"""
                    <div style="border: 2px solid #f66; border-radius: 10px; 
                                padding: 15px; margin: 10px 0; background: #fee;">
                        <div style="display: flex; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 20px; margin-right: 8px;">❌</span>
                            <strong style="color: #333;">Erro em {test_result['summary_type']}</strong>
                        </div>
                        <div style="color: #555; font-size: 14px; margin-bottom: 5px;">
                            <strong>Sessão:</strong> {session['session_id'][:12]}...
                        </div>
                        <div style="color: #555; font-size: 14px; margin-bottom: 5px;">
                            <strong>Diretório:</strong> {session['directory']}
                        </div>
                        <div style="color: #555; font-size: 14px; margin-bottom: 5px;">
                            <strong>Tempo:</strong> {test_result['execution_time']:.2f}s
                        </div>
                        <div style="color: #d63384; font-size: 14px; font-weight: bold;">
                            <strong>Erro:</strong> {sanitize_html_text(test_result.get('error', 'Erro desconhecido'))}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Detalhes do erro
                    with st.expander(f"🔍 Detalhes completos - {session['session_id'][:8]}"):
                        st.json(test_result)
            
            # Tabela de sucessos
            st.subheader("📋 Histórico Completo")
            
            results_data = []
            for key, test_result in st.session_state.test_results.items():
                session = test_result['session']
                result = test_result.get('result', {})
                
                is_success = test_result.get('success', result.get('success', False))
                status_icon = "✅" if is_success else "❌"
                
                results_data.append({
                    "Status": status_icon,
                    "Sessão": session['session_id'][:8] + "...",
                    "Diretório": session['directory'][:20] + "...",
                    "Tipo": test_result['summary_type'],
                    "Tempo (s)": f"{test_result['execution_time']:.2f}",
                    "Tokens": f"{result.get('metrics', {}).get('input_tokens', 0)}↑ {result.get('metrics', {}).get('output_tokens', 0)}↓" if is_success else "N/A",
                    "Custo": f"USD {result.get('metrics', {}).get('cost', 0):.6f}" if is_success else "N/A",
                    "Data": test_result['timestamp'][:19]
                })
            
            if results_data:
                st.dataframe(results_data, use_container_width=True)
            
        else:
            st.info("📊 Execute alguns testes para ver métricas aqui")

# 🏷️ Modal de Renomeação Global (fora de todas as estruturas de layout)
def show_rename_modal():
    """Exibe modal de renomeação fora da estrutura de colunas"""
    if st.session_state.get('show_rename_modal', False):
        session_id = st.session_state.get('rename_session_id', '')
        if not session_id:
            st.session_state.show_rename_modal = False
            return
            
        custom_names = load_session_names()
        current_name = custom_names.get(session_id, "")
        
        # Modal usando st.form para evitar problemas de aninhamento
        st.markdown("---")
        st.markdown("## 🏷️ Renomear Sessão")
        
        # Mostrar UUID atual
        st.code(f"UUID: {session_id}", language="text")
        
        # Form para renomeação
        with st.form("rename_form", clear_on_submit=False):
            # Campo de input
            new_name = st.text_input(
                "📝 Nome personalizado:", 
                value=current_name,
                placeholder="Digite um nome descritivo...",
                max_chars=100,
                help="Máximo 100 caracteres, sem símbolos especiais"
            )
            
            # Botões do form
            submitted = st.form_submit_button("💾 Salvar Nome", use_container_width=True, type="primary")
            
            if submitted and new_name.strip():
                is_valid, validation_result = validate_session_name(new_name.strip())
                if is_valid:
                    success, message = set_session_custom_name(session_id, validation_result)
                    if success:
                        st.success(f"✅ {message}")
                        st.session_state.show_rename_modal = False
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error(f"❌ {validation_result}")
        
        # Botões fora do form para outras ações
        if st.button("🤖 Gerar Nome com Claude Code SDK", key="ai_generate_name", use_container_width=True):
            with st.spinner("🤖 Analisando sessão..."):
                sessions = get_available_sessions()
                selected_session = None
                for session in sessions:
                    if session['session_id'] == session_id:
                        selected_session = session
                        break
                
                if selected_session:
                    ai_name = generate_session_name_with_claude(session_id, selected_session)
                    if ai_name:
                        st.success(f"🤖 Nome sugerido: '{ai_name}'")
                        # Definir o nome automaticamente
                        success, message = set_session_custom_name(session_id, ai_name)
                        if success:
                            st.success(f"✅ Nome salvo automaticamente!")
                            st.session_state.show_rename_modal = False
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("❌ Não foi possível gerar nome")
        
        if current_name:
            if st.button("↩️ Restaurar UUID Original", key="restore_uuid", use_container_width=True):
                success, message = remove_session_custom_name(session_id)
                if success:
                    st.success(f"✅ {message}")
                    st.session_state.show_rename_modal = False
                    time.sleep(0.5)
                    st.rerun()
        
        if st.button("❌ Cancelar", key="cancel_rename", use_container_width=True):
            st.session_state.show_rename_modal = False
            st.rerun()
        
        st.markdown("---")

# 📁 Modal de Renomeação de Projetos
def show_project_rename_modal():
    """Modal para renomeação de projetos"""
    if st.session_state.get('show_project_rename_modal', False):
        project_dir = st.session_state.get('project_to_rename', '')
        if not project_dir:
            st.session_state.show_project_rename_modal = False
            return
            
        project_custom_names = load_project_names()
        current_name = project_custom_names.get(project_dir, "")
        
        st.markdown("---")
        st.markdown("## 📁 Renomear Projeto")
        
        # Mostrar nome original
        st.code(f"Diretório Original: {project_dir}", language="text")
        
        # Preview do nome automático
        auto_name = clean_project_name(project_dir)
        st.info(f"🤖 Nome Automático: **{auto_name}**")
        
        # Form para renomeação
        with st.form("rename_project_form", clear_on_submit=False):
            new_name = st.text_input(
                "📝 Nome personalizado do projeto:", 
                value=current_name,
                placeholder=auto_name,  # Usar nome automático como placeholder
                max_chars=100,
                help="Deixe vazio para usar nome automático"
            )
            
            submitted = st.form_submit_button("💾 Salvar Nome do Projeto", use_container_width=True, type="primary")
            
            if submitted:
                final_name = new_name.strip() if new_name.strip() else auto_name
                
                is_valid, validation_result = validate_session_name(final_name)
                if is_valid:
                    success, message = set_project_custom_name(project_dir, validation_result)
                    if success:
                        st.success(f"✅ Projeto renomeado: '{validation_result}'")
                        st.session_state.show_project_rename_modal = False
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                else:
                    st.error(f"❌ {validation_result}")
        
        # Botões extras
        if current_name and st.button("↩️ Usar Nome Automático", key="use_auto_name", use_container_width=True):
            # Remove nome personalizado para usar automático
            names = load_project_names()
            if project_dir in names:
                names.pop(project_dir)
                save_project_names(names)
            st.success(f"✅ Agora usando nome automático: '{auto_name}'")
            st.session_state.show_project_rename_modal = False
            time.sleep(0.5)
            st.rerun()
        
        if st.button("❌ Cancelar", key="cancel_project_rename", use_container_width=True):
            st.session_state.show_project_rename_modal = False
            st.rerun()
        
        st.markdown("---")

if __name__ == "__main__":
    main()
    
    # 🏷️ Modais de Renomeação no nível raiz (após main)
    show_rename_modal()
    show_project_rename_modal()