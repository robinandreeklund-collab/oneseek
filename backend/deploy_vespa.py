"""
Deploy Vespa Cloud application and feed test data
This script sets up the Vespa schema and feeds sample documents
"""

import os
import sys
from pyvespa import ApplicationPackage, Field, Schema, Document, RankProfile, HNSW
from pyvespa.deployment import VespaCloud
from pyvespa.io import VespaResponse
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


def create_vespa_application():
    """Create the Vespa application package with schema definition"""
    
    # Define the document schema
    rag_schema = Schema(
        name="rag",
        document=Document(
            fields=[
                Field(name="doc_id", type="string", indexing=["summary", "attribute"]),
                Field(name="title", type="string", indexing=["summary", "index"]),
                Field(name="content", type="string", indexing=["summary", "index"]),
                Field(
                    name="embedding",
                    type="tensor<float>(x[384])",
                    indexing=["summary", "attribute", "index"],
                    ann=HNSW(
                        distance_metric="angular",
                        max_links_per_node=16,
                        neighbors_to_explore_at_insert=200
                    )
                )
            ]
        )
    )
    
    # Add rank profile for hybrid search (BM25 + semantic)
    rag_schema.add_rank_profile(
        RankProfile(
            name="hybrid",
            first_phase="nativeRank(title, content) + 0.5 * closeness(field, embedding)",
            inputs=[("query(q_embedding)", "tensor<float>(x[384])")],
        )
    )
    
    # Add simpler rank profile for semantic search only
    rag_schema.add_rank_profile(
        RankProfile(
            name="semantic",
            first_phase="closeness(field, embedding)",
            inputs=[("query(q_embedding)", "tensor<float>(x[384])")],
        )
    )
    
    # Create application package
    app_package = ApplicationPackage(
        name="oneseek-rag",
        schema=[rag_schema]
    )
    
    return app_package


def get_sample_documents():
    """Get sample documents for testing RAG"""
    return [
        {
            "doc_id": "1",
            "title": "AI Safety and Ethics",
            "content": "Experter inom AI-säkerhet varnar för flera potentiella risker med artificiell intelligens. "
                      "Bland de största hoten nämns kontrollförlusten över avancerade AI-system, "
                      "bias och diskriminering i algoritmer, samt användning av AI för cyberattacker. "
                      "Stuart Russell och andra forskare betonar vikten av att bygga in säkerhetsmekanismer "
                      "från början och utveckla AI-system som är alignade med mänskliga värderingar."
        },
        {
            "doc_id": "2",
            "title": "Sweden Geography and Culture",
            "content": "Sverige är ett nordeuropeiskt land med cirka 10 miljoner invånare. "
                      "Huvudstaden Stockholm är känd för sin skärgård och historiska gamlasta. "
                      "Landet är rikt på natur med skogar som täcker 69% av landytan. "
                      "Svensk kultur inkluderar traditioner som midsommar, lucia och fika. "
                      "Sverige är också känt för sitt innovativa företagsklimat med företag som Spotify, Klarna och Ericsson."
        },
        {
            "doc_id": "3",
            "title": "Machine Learning Fundamentals",
            "content": "Maskininlärning är en gren av artificiell intelligens där system lär sig från data "
                      "istället för att vara explicit programmerade. De tre huvudtyperna är supervised learning, "
                      "unsupervised learning och reinforcement learning. Neural nätverk, särskilt deep learning, "
                      "har revolutionerat området med framgångar inom bildanalys, språkförståelse och spel."
        },
        {
            "doc_id": "4",
            "title": "Climate Change Impact",
            "content": "Klimatförändringarna påverkar hela planeten med stigande temperaturer, "
                      "extremväder och höjda havsnivåer. FN:s klimatpanel IPCC varnar för allvarliga "
                      "konsekvenser om vi inte minskar utsläppen av växthusgaser drastiskt. "
                      "Lösningar inkluderar förnybar energi, elektrifiering av transporter och "
                      "naturbaserade lösningar som återplantering av skog."
        },
        {
            "doc_id": "5",
            "title": "Large Language Models",
            "content": "Stora språkmodeller (LLM) som GPT-4, Claude och Llama har transformerat "
                      "naturlig språkbehandling. Dessa modeller tränas på enorma mängder text och "
                      "kan utföra uppgifter som översättning, sammanfattning, kodgenerering och "
                      "konversation. RAG (Retrieval-Augmented Generation) kombinerar LLM:er med "
                      "kunskapsbaser för mer faktabaserade och uppdaterade svar."
        },
        {
            "doc_id": "6",
            "title": "Quantum Computing Basics",
            "content": "Kvantdatorer använder kvantmekaniska fenomen som superposition och entanglement "
                      "för att utföra beräkningar. Till skillnad från klassiska datorer som använder bits (0 eller 1), "
                      "använder kvantdatorer qubits som kan vara i flera tillstånd samtidigt. "
                      "Detta ger potentialen att lösa vissa problem exponentiellt snabbare än klassiska datorer."
        },
        {
            "doc_id": "7",
            "title": "Cybersecurity Best Practices",
            "content": "Cybersäkerhet är kritiskt i dagens digitala värld. Viktiga åtgärder inkluderar "
                      "starka och unika lösenord för varje tjänst, tvåfaktorsautentisering, regelbundna "
                      "säkerhetsuppdateringar, och försiktighet med phishing-attacker. För företag är "
                      "även penetrationstester, incidentresponsplaner och medarbetarutbildning essentiellt."
        },
        {
            "doc_id": "8",
            "title": "Renewable Energy Technologies",
            "content": "Förnybar energi inkluderar sol, vind, vatten och biomassa. Solpaneler har blivit "
                      "allt billigare och mer effektiva, medan vindkraft nu är kostnadseffektivt i många regioner. "
                      "Energilagring med batterier är nyckeln för att hantera intermittens från sol och vind. "
                      "Många länder satsar på 100% förnybar el inom de närmaste decennierna."
        },
        {
            "doc_id": "9",
            "title": "Blockchain and Cryptocurrencies",
            "content": "Blockchain är en distribuerad databasteknik där transaktioner lagras i block "
                      "som kedjas ihop kryptografiskt. Bitcoin var den första kryptovalutan, följt av "
                      "Ethereum som introducerade smarta kontrakt. Teknologin har potential inom "
                      "finanssektorn, supply chain management och digital identitet."
        },
        {
            "doc_id": "10",
            "title": "Space Exploration Milestones",
            "content": "Rymdforskning har gjort enorma framsteg från första satelliten Sputnik 1957 "
                      "till månlandningen 1969. Idag utforskar rovrar Mars, James Webb-teleskopet "
                      "studerar tidiga galaxer, och privata företag som SpaceX arbetar mot bemannade "
                      "Marsresor. Internationella rymdstationen ISS har varit i drift sedan 1998."
        },
        {
            "doc_id": "11",
            "title": "AI Bias and Fairness",
            "content": "AI-system kan ärva och förstärka bias från träningsdata. Detta har lett till "
                      "diskriminerande resultat i ansiktsigenkänning, rekrytering och kreditbedömning. "
                      "Forskare arbetar med fairness metrics, diverse träningsdata och algoritmisk "
                      "transparens för att bygga mer rättvisa AI-system. Det krävs både tekniska "
                      "och organisatoriska åtgärder för att adressera problemet."
        },
        {
            "doc_id": "12",
            "title": "Future of Work and Automation",
            "content": "Automatisering och AI kommer att förändra arbetsmarknaden radikalt. "
                      "Vissa jobb försvinner medan nya skapas. McKinsey uppskattar att 30% av "
                      "arbetstimmarna globalt skulle kunna automatiseras med befintlig teknik. "
                      "Vidareutbildning och livslångt lärande blir avgörande för arbetskraften. "
                      "Diskussionen om universal basic income intensifieras."
        },
        {
            "doc_id": "13",
            "title": "Vector Databases for AI",
            "content": "Vektordatabaser som Vespa, Pinecone och Weaviate är optimerade för att "
                      "lagra och söka i högdimensionella vektorer från embeddings. Detta är centralt "
                      "för RAG-applikationer, semantisk sökning och rekommendationssystem. "
                      "Vespa kombinerar vektorsökning med traditionell textmatching för hybrid search, "
                      "vilket ger bättre relevans än enbart semantisk sökning."
        },
        {
            "doc_id": "14",
            "title": "Edge AI and IoT",
            "content": "Edge AI innebär att köra AI-modeller lokalt på enheter istället för i molnet. "
                      "Detta ger fördelar som lägre latens, bättre integritet och minskad bandbredd. "
                      "IoT-enheter med edge AI kan fatta beslut i realtid utan nätverksanslutning. "
                      "Användningsområden inkluderar autonoma fordon, smart home och industriell automation."
        },
        {
            "doc_id": "15",
            "title": "Generative AI Creative Applications",
            "content": "Generativ AI som Stable Diffusion, Midjourney och DALL-E har revolutionerat "
                      "skapande av bilder, musik och text. Konstnärer och designers använder AI som "
                      "kreativt verktyg. Samtidigt väcker teknologin frågor om upphovsrätt, autenticitet "
                      "och AI-genererat innehålls påverkan på kreativa yrken. Nya affärsmodeller och "
                      "regleringar utvecklas för att hantera dessa utmaningar."
        }
    ]


def deploy_to_vespa_cloud(app_package, tenant: str, application: str):
    """Deploy application to Vespa Cloud"""
    
    vespa_cloud = VespaCloud(
        tenant=tenant,
        application=application,
        key_content=open(os.getenv("VESPA_KEY_PATH")).read(),
        application_package=app_package
    )
    
    print(f"Deploying to Vespa Cloud: {tenant}.{application}")
    print("This may take a few minutes...")
    
    # Deploy the application
    vespa_app = vespa_cloud.deploy()
    
    print("✓ Deployment successful!")
    return vespa_app


def feed_documents(vespa_app, documents):
    """Feed documents to Vespa with embeddings"""
    
    print("\nGenerating embeddings and feeding documents...")
    
    # Load embedding model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    
    for i, doc in enumerate(documents, 1):
        # Generate embedding
        text_to_embed = f"{doc['title']} {doc['content']}"
        embedding = model.encode(text_to_embed).tolist()
        
        # Prepare document with embedding
        vespa_doc = {
            **doc,
            "embedding": embedding
        }
        
        # Feed to Vespa
        response: VespaResponse = vespa_app.feed_data_point(
            schema="rag",
            data_id=doc["doc_id"],
            fields=vespa_doc
        )
        
        if response.is_successful():
            print(f"  ✓ Fed document {i}/{len(documents)}: {doc['title']}")
        else:
            print(f"  ✗ Failed to feed document {i}: {response.get_json()}")
    
    print(f"\n✓ Successfully fed {len(documents)} documents!")


def test_query(vespa_app):
    """Test a sample query"""
    print("\n" + "="*60)
    print("Testing query: 'AI-risker och säkerhet'")
    print("="*60)
    
    # Load embedding model
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    query_text = "AI-risker och säkerhet"
    query_embedding = model.encode(query_text).tolist()
    
    # Query with hybrid ranking
    response = vespa_app.query(
        yql="select doc_id, title, content from rag where userQuery() or ({targetHits:10}nearestNeighbor(embedding,q_embedding))",
        query=query_text,
        ranking="hybrid",
        body={
            "input.query(q_embedding)": query_embedding
        }
    )
    
    if response.is_successful():
        hits = response.hits
        print(f"\nFound {len(hits)} results:\n")
        for i, hit in enumerate(hits[:3], 1):
            fields = hit.get('fields', {})
            print(f"{i}. {fields.get('title', 'N/A')} (relevance: {hit.get('relevance', 0):.4f})")
            print(f"   {fields.get('content', '')[:150]}...")
            print()
    else:
        print(f"Query failed: {response.get_json()}")


def main():
    """Main deployment script"""
    
    # Check environment variables
    required_vars = ["VESPA_KEY_PATH", "VESPA_CERT_PATH"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"Error: Missing required environment variables: {', '.join(missing)}")
        print("\nPlease create a .env file with:")
        print("  VESPA_KEY_PATH=/path/to/private-key.pem")
        print("  VESPA_CERT_PATH=/path/to/certificate.pem")
        print("\nGet these from Vespa Cloud Console → Security")
        sys.exit(1)
    
    # Get tenant and application name
    tenant = input("Enter your Vespa Cloud tenant name: ").strip()
    if not tenant:
        print("Error: Tenant name is required")
        sys.exit(1)
    
    application = input("Enter application name [oneseek-rag]: ").strip() or "oneseek-rag"
    
    print("\n" + "="*60)
    print("OneSeek.ai - Vespa Cloud Deployment")
    print("="*60)
    
    # Create application package
    print("\n1. Creating Vespa application package...")
    app_package = create_vespa_application()
    print("   ✓ Application package created with 'rag' schema")
    
    # Deploy to Vespa Cloud
    print("\n2. Deploying to Vespa Cloud...")
    vespa_app = deploy_to_vespa_cloud(app_package, tenant, application)
    
    # Feed documents
    print("\n3. Feeding sample documents...")
    documents = get_sample_documents()
    feed_documents(vespa_app, documents)
    
    # Test query
    print("\n4. Testing query...")
    test_query(vespa_app)
    
    print("\n" + "="*60)
    print("✓ Deployment complete!")
    print("="*60)
    print(f"\nYour Vespa application is ready at:")
    print(f"  {vespa_app.url}")
    print(f"\nUpdate your .env file with:")
    print(f"  VESPA_URL={vespa_app.url}")
    print("\nYou can now start the FastAPI backend with:")
    print("  uvicorn app:app --reload --port 8001")


if __name__ == "__main__":
    main()
