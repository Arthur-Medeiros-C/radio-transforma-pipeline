"""Fábrica do cliente Supabase.

Responsabilidade única: construir e memoizar um `supabase.Client` a partir
das settings centralizadas, traduzindo falhas de configuração/construção
para uma excepção de domínio (`SupabaseClientError`).

Não acede a tabelas, storage ou RPC — isso pertence aos repositórios.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from radio_transforma.config import get_settings


class SupabaseClientError(RuntimeError):
    """Falha ao construir o cliente Supabase (config em falta ou inválida)."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Devolve um cliente Supabase memoizado para todo o processo.

    Preferência de chave:
      1. `service_role` (server-side, ignora RLS) — usado pela pipeline.
      2. `anon` (fallback, útil em testes e leitura pública).

    Levanta `SupabaseClientError` se URL ou chave estiverem em falta,
    ou se `create_client` falhar por qualquer motivo.
    """
    settings = get_settings()

    url = settings.supabase_url.strip()
    key = (
        settings.supabase_service_role_key.get_secret_value().strip()
        or settings.supabase_anon_key.get_secret_value().strip()
    )

    if not url:
        raise SupabaseClientError("SUPABASE_URL em falta. Define-a em .env ou no ambiente.")
    if not key:
        raise SupabaseClientError(
            "Nenhuma chave Supabase definida (SUPABASE_SERVICE_ROLE_KEY ou SUPABASE_ANON_KEY)."
        )

    try:
        return create_client(url, key)
    except Exception as exc:  # noqa: BLE001 — fronteira: traduzimos para domínio
        raise SupabaseClientError(f"Falha ao criar cliente Supabase: {exc}") from exc


def reset_supabase_client() -> None:
    """Limpa o cache do cliente. Existe para isolamento de testes."""
    get_supabase_client.cache_clear()
