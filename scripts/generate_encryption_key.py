"""Gera uma chave Fernet para criptografia de campos sensíveis (LGPD).
Copie a chave gerada para a variável ENCRYPTION_KEY no .env"""

from cryptography.fernet import Fernet


def main():
    key = Fernet.generate_key().decode()
    print("Chave Fernet gerada com sucesso!")
    print(f"\nENCRYPTION_KEY={key}")
    print("\nCopie a linha acima para o seu arquivo .env")


if __name__ == "__main__":
    main()
