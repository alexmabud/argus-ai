"""Script para gerar chave de criptografia Fernet para LGPD.

Gera uma chave criptográfica segura usando Fernet e exibe instruções
de como configurá-la no arquivo de variáveis de ambiente (.env).

A chave gerada deve ser usada na variável ENCRYPTION_KEY do .env
para criptografar campos sensíveis (CPF, dados pessoais) no banco.
"""

from cryptography.fernet import Fernet


def main() -> None:
    """Gera nova chave Fernet e printa instruções de configuração.

    Cria uma chave criptográfica segura usando Fernet e exibe
    no console o comando para configurá-la no arquivo .env.

    Returns:
        None
    """
    key = Fernet.generate_key().decode()
    print("Chave Fernet gerada com sucesso!")
    print(f"\nENCRYPTION_KEY={key}")
    print("\nCopie a linha acima para o seu arquivo .env")


if __name__ == "__main__":
    main()
