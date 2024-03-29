import logging
from gym.envs.registration import register

logger = logging.getLogger(__name__)

register(
    id='Platformer-v0',
    entry_point='gym_platformer.envs:PlatformerEnv',
    reward_threshold=1000,
    max_episode_steps=1000,
    nondeterministic = True,
)
