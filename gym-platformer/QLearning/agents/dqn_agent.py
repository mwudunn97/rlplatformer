import tensorflow as tf
import numpy as np

from QLearning.infrastructure.dqn_utils import MemoryOptimizedReplayBuffer, PiecewiseSchedule, get_wrapper_by_name
from QLearning.policies.argmax_policy import ArgMaxPolicy
from QLearning.critics.dqn_critic import DQNCritic
import gym_platformer

def log_episode(env):
    episode_rewards = get_wrapper_by_name(env, "Monitor").get_episode_rewards()
    episode_length = get_wrapper_by_name(env, "Monitor").get_episode_lengths()
    last_episode_reward = -3000
    if len(episode_rewards) > 0:
        last_episode_reward = episode_rewards[-1]
    
    print("Current Episode: " + str(len(episode_length)))
    print("Episode Reward: %f" % last_episode_reward)
    print('Done logging...\n\n')

class DQNAgent(object):
    def __init__(self, sess, env, agent_params):

        self.env = env
        self.sess = sess
        self.agent_params = agent_params
        self.batch_size = agent_params['batch_size']
        self.last_obs = self.env.reset()

        self.num_actions = agent_params['ac_dim']
        self.learning_starts = agent_params['learning_starts']
        self.learning_freq = agent_params['learning_freq']
        self.target_update_freq = agent_params['target_update_freq']
        self.learning_rate = agent_params['learning_rate']

        self.replay_buffer_idx = None
        self.exploration = agent_params['exploration_schedule']
        self.optimizer_spec = agent_params['optimizer_spec']

        self.critic = DQNCritic(sess, agent_params, self.optimizer_spec)
        self.actor = ArgMaxPolicy(sess, self.critic)

        lander = agent_params['env_name'] == 'LunarLander-v2'
        self.replay_buffer = MemoryOptimizedReplayBuffer(
            agent_params['replay_buffer_size'], agent_params['frame_history_len'], lander=lander)
        self.t = 0
        self.num_param_updates = 0

    def add_to_replay_buffer(self, paths):
        pass

    def step_env(self, render=False):

        """
            Step the env and store the transition

            At the end of this block of code, the simulator should have been
            advanced one step, and the replay buffer should contain one more transition.

            Note that self.last_obs must always point to the new latest observation.
        """

        # TODO store the latest observation into the replay buffer
        # HINT: see replay buffer's function store_frame
        self.replay_buffer_idx = self.replay_buffer.store_frame(self.last_obs)

        eps = self.exploration.value(self.t)
        # TODO use epsilon greedy exploration when selecting action
        # HINT: take random action 
            # with probability eps (see np.random.random())
            # OR if your current step number (see self.t) is less that self.learning_starts
        perform_random_action = (np.random.random() < eps) or (self.t < self.learning_starts)

        if perform_random_action:
            action = self.env.action_space.sample()
        else:
            # TODO query the policy to select action
            # HINT: you cannot use "self.last_obs" directly as input
            # into your network, since it needs to be processed to include context
            # from previous frames. 
            # Check out the replay buffer, which has a function called
            # encode_recent_observation that will take the latest observation
            # that you pushed into the buffer and compute the corresponding
            # input that should be given to a Q network by appending some
            # previous frames.
            enc_last_obs = self.replay_buffer.encode_recent_observation()
            enc_last_obs = enc_last_obs[None, :]

            # TODO query the policy with enc_last_obs to select action
            action = self.actor.get_action(enc_last_obs)
            action = action[0]

        # TODO take a step in the environment using the action from the policy
        # HINT1: remember that self.last_obs must always point to the newest/latest observation
        # HINT2: remember the following useful function that you've seen before:
            #obs, reward, done, info = env.step(action)


        self.last_obs, reward, done, info = self.env.step(action)
    
        # TODO store the result of taking this action into the replay buffer
        # HINT1: see replay buffer's store_effect function
        # HINT2: one of the arguments you'll need to pass in is self.replay_buffer_idx from above
        self.replay_buffer.store_effect(self.replay_buffer_idx, action, reward, done)

        # TODO if taking this step resulted in done, reset the env (and the latest observation)
        if render:
            self.env.render()
        if done:
            if render:
                log_episode(self.env)
            self.last_obs = self.env.reset()

    def sample(self, batch_size):
        if self.replay_buffer.can_sample(self.batch_size):
            return self.replay_buffer.sample(batch_size)
        else:
            return [],[],[],[],[]

    def train(self, ob_no, ac_na, re_n, next_ob_no, terminal_n):

        """
            Here, you should train the DQN agent.
            This consists of training the critic, as well as periodically updating the target network.
        """

        loss = 0.0
        if (self.t > self.learning_starts and \
                self.t % self.learning_freq == 0 and \
                self.replay_buffer.can_sample(self.batch_size)):

            # TODO populate all placeholders necessary for calculating the critic's total_error
            # HINT: obs_t_ph, act_t_ph, rew_t_ph, obs_tp1_ph, done_mask_ph
            learning_rate = self.optimizer_spec.lr_schedule.value(self.t)
            #
            if self.learning_rate:
                learning_rate = self.learning_rate
            feed_dict = {
                self.critic.learning_rate: learning_rate,
                self.critic.obs_t_ph: ob_no,
                self.critic.act_t_ph: ac_na,
                self.critic.rew_t_ph: re_n,
                self.critic.obs_tp1_ph: next_ob_no,
                self.critic.done_mask_ph: terminal_n,
            }

            # TODO: create a LIST of tensors to run in order to 
            # train the critic as well as get the resulting total_error
            tensors_to_run = [self.critic.train_fn, self.critic.total_error]
            loss, _ = self.sess.run(tensors_to_run, feed_dict=feed_dict)
            # Note: remember that the critic's total_error value is what you
            # created to compute the Bellman error in a batch, 
            # and the critic's train function performs a gradient step 
            # and update the network parameters to reduce that total_error.

            # TODO: use sess.run to periodically update the critic's target function
            # HINT: see update_target_fn
            if self.num_param_updates % self.target_update_freq == 0:
                self.sess.run(self.critic.update_target_fn, feed_dict=feed_dict)

            self.num_param_updates += 1

        self.t += 1
        return loss
