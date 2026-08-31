from download_zip import baixar_arquivo, buscar_data_atual
from sql import verificar_tabelas, inserir_arquivo_no_banco_dados
from listar_arquivos import buscar_arquivos

tabelas_verificadas = []

def main() -> None:
    verificar_tabelas()

    for objeto in buscar_arquivos(buscar_data_atual()):
        nome_arquivo = objeto["nome"]
        tamanho_arquivo = objeto["tamanho"]
        while True:
            print(f"Nome: {nome_arquivo} | Tamanho: {tamanho_arquivo}")
            print("Deseja baixar esse arquivo? s / n")
            user_input = input("-> ").strip().lower()
            if user_input == 's' or user_input == 'n':
                break

        if user_input == 's':
            nome_arquivo = nome_arquivo[:-4] # Remove o  .zip

            baixar_arquivo(nome_arquivo)
            #inserir_arquivo_no_banco_dados(nome_arquivo)

if __name__ == "__main__":
    main()