"""
Servicio de Autenticación para SERPY
Gestiona el registro, login y autenticación de usuarios
"""
import streamlit as st
import streamlit_authenticator as stauth
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
import re
from repositories.mongo_repository import MongoRepository
from config.settings import settings
import bcrypt
import jwt
import extra_streamlit_components as stx
import secrets


class AuthService:
    """Servicio para gestionar la autenticación de usuarios"""
    
    def __init__(self):
        """Inicializa el servicio de autenticación"""
        self.mongo = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
        self.collection_name = "usuarios"
        self.sessions_collection = "user_sessions"
        self.secret_key = getattr(settings, 'secret_key', 'serpy-secret-key-2025')
        
    def validate_email(self, email: str) -> bool:
        """
        Valida el formato del email
        
        Args:
            email: Email a validar
            
        Returns:
            True si el email es válido, False si no
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """
        Valida la contraseña
        
        Args:
            password: Contraseña a validar
            
        Returns:
            Tupla (es_válida, mensaje_error)
        """
        if len(password) < 6:
            return False, "La contraseña debe tener al menos 6 caracteres"
        return True, ""
    
    def hash_password(self, password: str) -> str:
        """
        Hashea una contraseña usando bcrypt
        
        Args:
            password: Contraseña en texto plano
            
        Returns:
            Hash de la contraseña
        """
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verifica una contraseña contra su hash
        
        Args:
            password: Contraseña en texto plano
            hashed: Hash almacenado
            
        Returns:
            True si la contraseña es correcta
        """
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def email_exists(self, email: str) -> bool:
        """
        Verifica si un email ya está registrado
        
        Args:
            email: Email a verificar
            
        Returns:
            True si el email ya existe
        """
        user = self.mongo.find_one(
            {"email": email.lower()},
            collection_name=self.collection_name
        )
        return user is not None
    
    def register_user(self, name: str, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Registra un nuevo usuario
        
        Args:
            name: Nombre completo del usuario
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Tupla (éxito, mensaje, datos_usuario)
        """
        # Validar nombre
        if len(name.strip()) < 2:
            return False, "El nombre debe tener al menos 2 caracteres", None
        
        # Validar email
        if not self.validate_email(email):
            return False, "El formato del email no es válido", None
        
        # Verificar si el email ya existe
        if self.email_exists(email):
            return False, "Este email ya está registrado", None
        
        # Validar contraseña
        valid_password, error_msg = self.validate_password(password)
        if not valid_password:
            return False, error_msg, None
        
        # Crear usuario
        try:
            user_data = {
                "name": name.strip(),
                "email": email.lower().strip(),
                "password": self.hash_password(password),
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "is_active": True
            }
            
            user_id = self.mongo.insert_one(user_data, self.collection_name)
            
            if user_id:
                user_data["_id"] = user_id
                return True, "Usuario registrado exitosamente", user_data
            else:
                return False, "Error al crear el usuario", None
                
        except Exception as e:
            return False, f"Error al registrar usuario: {str(e)}", None
    
    def login_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Intenta hacer login con email y contraseña
        
        Args:
            email: Email del usuario
            password: Contraseña en texto plano
            
        Returns:
            Tupla (éxito, mensaje, datos_usuario)
        """
        # Buscar usuario por email
        user = self.mongo.find_one(
            {"email": email.lower()},
            collection_name=self.collection_name
        )
        
        if not user:
            return False, "Email o contraseña incorrectos", None
        
        # Verificar contraseña
        if not self.verify_password(password, user["password"]):
            return False, "Email o contraseña incorrectos", None
        
        # Verificar si el usuario está activo
        if not user.get("is_active", True):
            return False, "Esta cuenta está desactivada", None
        
        # Actualizar último login
        self.mongo.update_one(
            {"_id": user["_id"]},
            {"last_login": datetime.now().isoformat()},
            collection_name=self.collection_name
        )
        
        # No devolver la contraseña
        user.pop("password", None)
        
        return True, "Login exitoso", user
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """
        Obtiene un usuario por su ID
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Datos del usuario o None
        """
        user = self.mongo.find_one(
            {"_id": user_id},
            collection_name=self.collection_name
        )
        
        if user:
            user.pop("password", None)
        
        return user
    
    def create_session_token(self, user_id: str) -> str:
        """
        Crea un token de sesión para el usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Token de sesión
        """
        # Crear token único
        token = secrets.token_urlsafe(32)
        
        # Guardar en base de datos
        session_data = {
            "token": token,
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "is_active": True
        }
        
        self.mongo.insert_one(session_data, self.sessions_collection)
        
        return token
    
    def validate_session_token(self, token: str) -> Optional[Dict]:
        """
        Valida un token de sesión y devuelve los datos del usuario
        
        Args:
            token: Token de sesión
            
        Returns:
            Datos del usuario o None si el token no es válido
        """
        if not token:
            return None
            
        # Buscar sesión
        session = self.mongo.find_one(
            {"token": token, "is_active": True},
            collection_name=self.sessions_collection
        )
        
        if not session:
            return None
        
        # Verificar expiración
        expires_at = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expires_at:
            # Marcar como inactiva
            self.mongo.update_one(
                {"token": token},
                {"is_active": False},
                collection_name=self.sessions_collection
            )
            return None
        
        # Obtener usuario
        user = self.get_user_by_id(session["user_id"])
        return user
    
    def logout_user(self, token: str) -> bool:
        """
        Cierra la sesión del usuario invalidando el token
        
        Args:
            token: Token de sesión
            
        Returns:
            True si se cerró la sesión correctamente
        """
        if not token:
            return False
            
        return self.mongo.update_one(
            {"token": token},
            {"is_active": False},
            collection_name=self.sessions_collection
        )
