from flask import Flask, render_template, request, Response, jsonify, send_from_directory
from langchain_community.llms import Ollama
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma
import sqlite3
import time

app = Flask(__name__) #init

DATABASE_DIRECTORY = "db"
PDF_DIRECTORY = 'pdfs'
MODEL_PATH = "llama3.1"

language_model = Ollama(model=MODEL_PATH, temperature=0)
embedder = FastEmbedEmbeddings()

document_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000, chunk_overlap=60, length_function=len, is_separator_regex=False
)

query_prompt = PromptTemplate.from_template(
    """ 
    <s>[INST] You are a document assistant specialized in retrieving information. Analyze the context and provide answers based only on the available information. If the answer is not in the documents provided, clearly state, ‘The information is not available in the context.’. Answer in german. [/INST] </s>
    [INST] {input}
           Context: {context}
           Answer:
    [/INST]
"""
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    file = request.files["file"]
    file_path = f"{PDF_DIRECTORY}/{file.filename}"
    file.save(file_path)

    loader = PDFPlumberLoader(file_path)
    documents = loader.load_and_split()
    document_chunks = document_splitter.split_documents(documents)

    vector_store = Chroma.from_documents(documents=document_chunks, embedding=embedder, persist_directory=DATABASE_DIRECTORY)
    vector_store.persist()

    response = {
        "status": "Upload successful",
        "filename": file.filename,
        "doc_count": len(documents),
        "chunk_count": len(document_chunks)
    }
    return response

@app.route("/query_pdf", methods=["POST"])
def query_pdf():
    json_data = request.json
    user_query = json_data.get("query")
    print(user_query)
    vector_store = Chroma(persist_directory=DATABASE_DIRECTORY, embedding_function=embedder)
    
    retriever = vector_store.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 3, "score_threshold": 0.5},
    )
    
    document_chain = create_stuff_documents_chain(language_model, query_prompt)
    retrieval_chain = create_retrieval_chain(retriever, document_chain)
    result = retrieval_chain.invoke({"input": user_query})

    sources = [{"source": doc.metadata["source"], "page_content": doc.page_content} for doc in result["context"]]
    response_data = {"answer": result["answer"], "sources": sources}
    
    return response_data

@app.route('/pdfs/<filename>')
def serve_pdf(filename):
    return send_from_directory(PDF_DIRECTORY, filename)

@app.route('/interactive_chat')
def interactive_chat():
    return render_template('stream.html')

@app.route('/stream_response', methods=['POST'])
def stream_response():
    data = request.json
    user_query = data.get('query', '')
    return Response(generate_response_stream(user_query), content_type='text/plain')

def generate_response_stream(prompt):
    response_stream = language_model.stream(prompt)
    
    for chunk in response_stream: 
        yield f"{chunk}"  
        time.sleep(0.1)

DB_PATH = 'db/chroma.sqlite3'

@app.route('/list_sources', methods=['GET'])
def list_sources():
    try:
        source_files = get_available_sources()
        print(source_files)
        return jsonify(source_files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_available_sources():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = "SELECT DISTINCT string_value FROM embedding_metadata WHERE key='source'"
        cursor.execute(query)
        rows = cursor.fetchall()
        
        sources = []
        for row in rows:
            file_path = row[0]
            if "pdfs/" in file_path:
                pdf_name = file_path.split("pdfs/")[-1]
                sources.append(pdf_name)
            else:
                sources.append(file_path)
        
        conn.close()
        
        print(sources)
        
        return sources
    except Exception as e:
        raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)