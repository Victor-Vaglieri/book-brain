from sentence_transformers import SentenceTransformer, util

def compare_models():
    print("Iniciando o teste de comparação de Embeddings...")
    print("Aguarde, os modelos estão sendo carregados (se for a primeira vez, o modelo novo será baixado)...\n")
    
    model_antigo = SentenceTransformer('all-MiniLM-L6-v2')
    
    model_novo = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

    documentos = [
        "A taxa de juros (Selic) afeta diretamente o controle da inflação no país.",
        "Para realizar a manutenção preventiva do motor do veículo, desligue sempre a chave de ignição antes.",
        "O rendimento das contas de poupança tem caído com a redução dos juros básicos da economia.",
        "O cachorro brincou no parque a tarde toda com sua bolinha e depois dormiu profundamente.",
        "A inteligência artificial ajuda a processar e entender documentos complexos de forma automatizada.",
        "O gato subiu no telhado porque estava assustado com o barulho dos fogos de artifício."
    ]
    
    perguntas = [
        "Qual o impacto da taxa básica na rentabilidade de quem guarda dinheiro no banco?",
        "O que devo fazer antes de consertar o carro?",
        "Os bichos de estimação gastaram energia hoje?"
    ]
    
    for pergunta in perguntas:
        print(f"\n" + "="*80)
        print(f"PERGUNTA FEITA PELO USUÁRIO: '{pergunta}'")
        print("="*80)
        
        for name, model in [("all-MiniLM-L6-v2 (MODELO ATUAL)", model_antigo), 
                            ("paraphrase-multilingual-MiniLM-L12-v2 (MODELO RECOMENDADO)", model_novo)]:
            
            doc_emb = model.encode(documentos)
            query_emb = model.encode([pergunta])
            
            hits = util.semantic_search(query_emb, doc_emb, top_k=2)[0]
            
            print(f"\n--- Resultados usando: {name} ---")
            for i, hit in enumerate(hits):
                doc_idx = hit['corpus_id']
                score = hit['score']
                print(f"{i+1}º Lugar (Relevância: {score:.4f}) -> {documentos[doc_idx]}")

if __name__ == "__main__":
    compare_models()
