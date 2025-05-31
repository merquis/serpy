"""
Componentes comunes de UI reutilizables para Streamlit
"""
import streamlit as st
from typing import Optional, List, Dict, Any, Callable
from config import config

class Card:
    """Componente de tarjeta mejorado"""
    @staticmethod
    def render(
        title: str,
        content: Any,
        icon: Optional[str] = None,
        subtitle: Optional[str] = None,
        expandable: bool = False,
        expanded: bool = True
    ):
        """Renderiza una tarjeta con estilo mejorado"""
        if expandable:
            with st.expander(f"{icon} {title}" if icon else title, expanded=expanded):
                if subtitle:
                    st.caption(subtitle)
                if isinstance(content, str):
                    st.write(content)
                else:
                    content()
        else:
            container = st.container()
            with container:
                if icon or title:
                    col1, col2 = st.columns([0.1, 0.9]) if icon else [1]
                    if icon:
                        col1.write(icon)
                        col2.subheader(title)
                    else:
                        st.subheader(title)
                
                if subtitle:
                    st.caption(subtitle)
                
                if isinstance(content, str):
                    st.write(content)
                else:
                    content()

class ProgressBar:
    """Barra de progreso mejorada"""
    @staticmethod
    def render(
        current: int,
        total: int,
        text: Optional[str] = None,
        show_percentage: bool = True
    ):
        """Renderiza una barra de progreso con texto opcional"""
        progress = current / total if total > 0 else 0
        
        if text:
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                st.write(text)
            with col2:
                if show_percentage:
                    st.write(f"{progress*100:.1f}%")
        
        st.progress(progress)

class Alert:
    """Sistema de alertas mejorado"""
    @staticmethod
    def success(message: str, icon: bool = True):
        """Muestra una alerta de éxito"""
        icon_str = config.ui.icons["success"] if icon else ""
        st.success(f"{icon_str} {message}")
    
    @staticmethod
    def error(message: str, icon: bool = True):
        """Muestra una alerta de error"""
        icon_str = config.ui.icons["error"] if icon else ""
        st.error(f"{icon_str} {message}")
    
    @staticmethod
    def warning(message: str, icon: bool = True):
        """Muestra una alerta de advertencia"""
        icon_str = config.ui.icons["warning"] if icon else ""
        st.warning(f"{icon_str} {message}")
    
    @staticmethod
    def info(message: str, icon: bool = True):
        """Muestra una alerta informativa"""
        icon_str = config.ui.icons["info"] if icon else ""
        st.info(f"{icon_str} {message}")

class Button:
    """Botones mejorados con iconos"""
    @staticmethod
    def primary(
        label: str,
        icon: Optional[str] = None,
        key: Optional[str] = None,
        disabled: bool = False,
        on_click: Optional[Callable] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        use_container_width: bool = False
    ) -> bool:
        """Renderiza un botón primario"""
        button_label = f"{icon} {label}" if icon else label
        return st.button(
            button_label,
            key=key,
            disabled=disabled,
            on_click=on_click,
            args=args,
            kwargs=kwargs,
            use_container_width=use_container_width,
            type="primary"
        )
    
    @staticmethod
    def secondary(
        label: str,
        icon: Optional[str] = None,
        key: Optional[str] = None,
        disabled: bool = False,
        on_click: Optional[Callable] = None,
        args: Optional[tuple] = None,
        kwargs: Optional[dict] = None,
        use_container_width: bool = False
    ) -> bool:
        """Renderiza un botón secundario"""
        button_label = f"{icon} {label}" if icon else label
        return st.button(
            button_label,
            key=key,
            disabled=disabled,
            on_click=on_click,
            args=args,
            kwargs=kwargs,
            use_container_width=use_container_width,
            type="secondary"
        )

class LoadingSpinner:
    """Spinner de carga mejorado"""
    @staticmethod
    def show(text: str = "Procesando...", icon: bool = True):
        """Muestra un spinner de carga"""
        icon_str = config.ui.icons["loading"] if icon else ""
        return st.spinner(f"{icon_str} {text}")

class Tabs:
    """Sistema de pestañas mejorado"""
    @staticmethod
    def render(
        tabs: List[Dict[str, Any]],
        key: Optional[str] = None
    ):
        """
        Renderiza pestañas con contenido
        tabs: Lista de diccionarios con 'label', 'icon' (opcional) y 'content' (función)
        """
        tab_labels = []
        for tab in tabs:
            label = tab['label']
            if 'icon' in tab:
                label = f"{tab['icon']} {label}"
            tab_labels.append(label)
        
        tab_containers = st.tabs(tab_labels)
        
        for i, (tab_container, tab) in enumerate(zip(tab_containers, tabs)):
            with tab_container:
                if callable(tab['content']):
                    tab['content']()
                else:
                    st.write(tab['content'])

class FileUploader:
    """Componente mejorado para carga de archivos"""
    @staticmethod
    def render(
        label: str,
        file_types: List[str],
        key: Optional[str] = None,
        help_text: Optional[str] = None,
        accept_multiple: bool = False
    ):
        """Renderiza un cargador de archivos mejorado"""
        with st.container():
            file = st.file_uploader(
                label,
                type=file_types,
                key=key,
                help=help_text,
                accept_multiple_files=accept_multiple
            )
            
            if file:
                if not accept_multiple:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"📄 {file.name}")
                    with col2:
                        st.caption(f"{file.size / 1024:.1f} KB")
                else:
                    for f in file:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"📄 {f.name}")
                        with col2:
                            st.caption(f"{f.size / 1024:.1f} KB")
            
            return file

class MetricCard:
    """Tarjeta de métrica mejorada"""
    @staticmethod
    def render(
        label: str,
        value: Any,
        delta: Optional[Any] = None,
        delta_color: str = "normal",
        help_text: Optional[str] = None
    ):
        """Renderiza una tarjeta de métrica con estilo mejorado"""
        st.metric(
            label=label,
            value=value,
            delta=delta,
            delta_color=delta_color,
            help=help_text
        )

class SelectBox:
    """SelectBox mejorado con búsqueda"""
    @staticmethod
    def render(
        label: str,
        options: List[Any],
        index: int = 0,
        format_func: Optional[Callable] = None,
        key: Optional[str] = None,
        help_text: Optional[str] = None,
        placeholder: Optional[str] = None,
        disabled: bool = False
    ):
        """Renderiza un selectbox mejorado"""
        return st.selectbox(
            label,
            options,
            index=index,
            format_func=format_func,
            key=key,
            help=help_text,
            placeholder=placeholder,
            disabled=disabled
        )

class DataDisplay:
    """Componente para mostrar datos de forma elegante"""
    @staticmethod
    def json(
        data: Dict[str, Any],
        title: Optional[str] = None,
        expanded: bool = True,
        height: Optional[int] = None
    ):
        """Muestra datos JSON de forma elegante"""
        if title:
            st.subheader(title)
        
        if height:
            st.json(data, expanded=expanded)
        else:
            st.json(data, expanded=expanded)
    
    @staticmethod
    def code(
        code: str,
        language: str = "python",
        title: Optional[str] = None
    ):
        """Muestra código con resaltado de sintaxis"""
        if title:
            st.subheader(title)
        st.code(code, language=language)

class EmptyState:
    """Componente para estados vacíos"""
    @staticmethod
    def render(
        title: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        action_label: Optional[str] = None,
        action_callback: Optional[Callable] = None
    ):
        """Renderiza un estado vacío con acción opcional"""
        container = st.container()
        with container:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if icon:
                    st.markdown(f"<h1 style='text-align: center'>{icon}</h1>", unsafe_allow_html=True)
                
                st.markdown(f"<h3 style='text-align: center'>{title}</h3>", unsafe_allow_html=True)
                
                if description:
                    st.markdown(f"<p style='text-align: center'>{description}</p>", unsafe_allow_html=True)
                
                if action_label and action_callback:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button(action_label, use_container_width=True):
                        action_callback() 