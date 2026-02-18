import asyncio
import sys
import os
import logging

# Add the backend directory to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from src.core.database import init_db
# from src.common.youtube_tools import YouTubeTools
from src.api.chat import InitRequest, init_threads
from src.agents.chat_agent import YTAgentState, YoutubeVideo, agent
from langchain.messages import HumanMessage
from sqlmodel.ext.asyncio.session import AsyncSession
from src.common.services import vector_store
from src.core.database import engine



async def run_test():
    logger.info("Starting Chat Flow Test (Real Services)...")

    # Initialize DB
    logger.info("Initializing Database...")
    await init_db()

    # Create a session for init_chat
    async with AsyncSession(engine, expire_on_commit=False) as session:
        # 1. Test init_chat with a REAL YouTube video
        # Using a short, stable video for testing: "Google Search - 60s" or similar
        # Let's use a known safe URL. 
        # Example: "Me at the zoo" - the first youtube video (short) -> https://www.youtube.com/watch?v=jNQXAC9IVRw
        test_url = "https://www.youtube.com/watch?v=U_zWBOV_bng"
        
        logger.info(f"Testing init_chat with URL: {test_url}")
        request = InitRequest(youtube_url=test_url)
        
        try:
            init_result = await init_threads(request, session)
            logger.info("Init Chat Result:")
            print(init_result)
            
            logger.info("✅ init_chat passed")
            return 
        except Exception as e:
            logger.error(f"❌ init_chat failed: {e}")
            import traceback
            traceback.print_exc()
            return

        # 2. Test Chat Agent (Graph)
        logger.info("Testing Chat Agent Graph...")
        
        app = workflow.compile()
        
        # Real question about the video
        question = "What is the guy in the video talking about?"
        logger.info(f"Asking question: {question}")

        initial_state = {"messages": [("user", question)]}
        config = {"configurable": {"thread_id": thread_id, "video_id": video_id}}
        
        try:
            final_state = await app.ainvoke(initial_state, config=config)
            
            messages = final_state.get("messages")
            last_msg = messages[-1]
            
            logger.info("Agent Response:")
            print(f"> {last_msg.content}")
            
            if last_msg.content:
                logger.info("✅ Chat Agent passed (Response received)")
            else:
                logger.warning("⚠️ Chat Agent returned empty response")
            
        except Exception as e:
            logger.error(f"❌ Chat Agent failed: {e}")
            import traceback
            traceback.print_exc()

async def test():
    question = "names taken in the video"
    video1 = YoutubeVideo(
        video_id="U_zWBOV_bng",
        title="Ro Khanna reveals 6 redacted names in the Epstein files on the House floor",
        summary="Congressmen Massie and the Speaker visited the DOJ regarding unredacted Epstein files, discovering significant redactions and the subsequent revelation of previously hidden powerful men only after their inquiry. This review exposed a disturbing pattern of file redactions allegedly protecting wealthy individuals involved with Jeffrey Epstein's island and abuse. The Speaker questions the lack of elite accountability in the US compared to other nations, highlighting a potential two-tiered justice system. The video emphasizes that billionaires who participated in or ignored underage rape on Epstein's island may escape consequences. Ultimately, the video calls for urgent investigations and prosecutions to ensure accountability and restore equitable justice for all."
        )
    
    input: YTAgentState = YTAgentState(
        messages=[
            HumanMessage(content= question)
            ],
        videos=[video1]
        )
    
    result = agent.invoke(
        input= input, # type: ignore
        config={"configurable": {"thread_id": "U_1zWBOV_bn43113"}},

    )
    print(result)
    return

if __name__ == "__main__":

  asyncio.run(test())

    # asyncio.run(run_test())
