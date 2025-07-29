from flask import Flask, render_template, jsonify, request, send_from_directory
from helper import load_pdf, text_split, download_huggingface_embedding
from pinecone import Pinecone
from pinecone import ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from prompt import *
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")


DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')
os.makedirs(DATA_FOLDER, exist_ok=True)

embeddings = download_huggingface_embedding()
index_name = "aichatbot"
pc = Pinecone(api_key=PINECONE_API_KEY)

def build_rag_chain(index_name):
    docsearch = PineconeVectorStore.from_existing_index(index_name=index_name, embedding=embeddings)
    retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k": 3})
    llm = ChatGoogleGenerativeAI(model="models/gemini-1.5-flash", temperature=0.0, google_api_key=GOOGLE_API_KEY)
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n{context}"),
        ("human", "{input}"),
    ])
    que_ans_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, que_ans_chain)

# Initial RAG setup (dummy index assumed)
try:
    rag_chain = build_rag_chain(index_name)
except Exception as e:
    print(f"Warning: Failed to load initial index '{index_name}':", e)
    rag_chain = None

@app.route("/ask", methods=["POST"])
def ask():
    if rag_chain is None:
        return jsonify({"reply": "Index not found. Please upload documents from admin panel first."})

    data = request.get_json()
    user_question = data.get("question", "")
    response = rag_chain.invoke({"input": user_question})
    return jsonify({"reply": response["answer"]})

@app.route('/admin/upload', methods=['POST'])
def upload_file():
    global rag_chain  # So we can overwrite the global rag_chain at runtime

    if 'file' not in request.files:
        return "No file part", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    save_path = os.path.join(DATA_FOLDER, file.filename)
    file.save(save_path)

    # ==== Pinecone Index Overwrite ====
    # Delete existing index if exists
    if index_name in [i.name for i in pc.list_indexes()]:
        pc.delete_index(index_name)

    # Create new index
    pc.create_index(
        name=index_name,
        dimension=384,  # Adjust based on embedding size
        metric='cosine',
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"
        )
    )

    # Rebuild vector store with new data
    extracted_data = load_pdf(data=DATA_FOLDER)
    text_chunks = text_split(extracted_data)
    PineconeVectorStore.from_documents(
        documents=text_chunks,
        index_name=index_name,
        embedding=embeddings
    )

    # Rebuild RAG chain immediately after upload
    rag_chain = build_rag_chain(index_name)

    return "New index created and loaded successfully!"

@app.route('/admin/files', methods=['GET'])
def list_files():
    files = os.listdir(DATA_FOLDER)
    return jsonify(files)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False, threaded=False)
