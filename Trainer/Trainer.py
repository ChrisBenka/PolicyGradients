import os
import tensorflow as tf
import time
import tqdm
from Replay import get_replay_buffer


class Trainer:
	def __init__(self, agent, env, visualizer, args, output_dir='./Experiments/', model_dir='./Models/'):
		assert isinstance(args, dict), "Expected args to be of type dict"
		for k, v in args:
			setattr(self, k, v)

		self._agent = agent
		self._env = env
		self._visualizer = visualizer
		self._replay_buffer = get_replay_buffer(args)

		self._output_dir = output_dir
		self._model_dir = model_dir

		self._set_check_point(args.model_dir)

		# prepare TensorBoard output
		self.writer = tf.summary.create_file_writer(self._output_dir)
		self.writer.set_as_default()

	def __call_(self):
		assert self._num_episodes is not None, "Expected _num_episodes to be defined"
		assert self._max_eps_steps is not None, "Expected _max_eps_steps to be defined"

		total_steps, running_reward = 0, 0

		with tqdm.trange(self._num_episodes) as t:
			for episode in t:
				obs, steps = self._env.reset(), 0
				episode_start_time, episode_reward = time.perf_counter(), 0

				for steps in range(self._max_eps_steps):
					if total_steps < self._n_warmup_steps:
						action = self._env.action_space.sample()
					else:
						action = self._agent.get_action(obs)

					next_obs, reward, done, _ = self._env.step(action)

					if self._show_progress_intvl is not None and self._show_progress_intvl % episode == 0:
						self._env.render()

					if self._replay_buffer is not None:
						self._replay_buffer.add(obs, action, next_obs, reward, done)

						if total_steps % self._agent.policy_update_interval == 0:
							samples = self._replay_buffer.sample(self._agent.batch_size)
							self._agent.train(samples)

					elif total_steps % self._agent.policy_update_interval == 0:
						self._agent.train()

					obs = next_obs

					if done:
						fps = steps / (time.perf_counter() - episode)
						running_reward = .99 * running_reward + .01 * episode_reward
						t.set_description(f"Episode {episode}")
						t.set_postfix(episode_reward=episode_reward, running_reward=running_reward, fps=fps)

						tf.summary.scalar(name="Common/training_reward", data=episode_reward)
						tf.summary.scalar(name="Common/training_episode_length", data=steps)

						self._replay_buffer.on_episode_end()

						if running_reward >= self._reward_threshold:
							print(f"\n Solved at episode {i}, average reward: {running_reward:.2f}")
							return

						obs = self._env.reset()
					if self._max_steps is not None and self._max_steps >= total_steps:
						tf.summary.flush()
						return

					if self._visualize:
						if self._visualizer is not None:
							self._visualizer.visualize()
						else:
							# todo implement default visualizer
							pass

		tf.summary.flush()

	def _set_check_point(self, model_dir):
		# Save and restore model
		self._checkpoint = tf.train.Checkpoint(agent=self._agent)
		self.checkpoint_manager = tf.train.CheckpointManager(
			self._checkpoint, directory=self._output_dir, max_to_keep=5)

		if model_dir is not None:
			assert os.path.isdir(model_dir)
			self._latest_path_ckpt = tf.train.latest_checkpoint(model_dir)
			self._checkpoint.restore(self._latest_path_ckpt)











