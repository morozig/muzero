"""

"""
import typing
from datetime import datetime

import numpy as np
import tensorflow as tf

from Coach import Coach
from Experimenter.players import MuZeroPlayer
from MuZero.MuMCTS import MuZeroMCTS
from utils import DotDict
from utils.selfplay_utils import GameHistory, sample_batch


class MuZeroCoach(Coach):
    """
    This class executes the self-play + learning. It uses the functions defined
    in Game and NeuralNet. args are specified in main.py.
    """

    def __init__(self, game, neural_net, args: DotDict, run_name: typing.Optional[str] = None) -> None:
        """

        :param game:
        :param neural_net:
        :param args:
        """
        super().__init__(game, neural_net, args, MuZeroMCTS, MuZeroPlayer)

        if run_name is None:
            run_name = datetime.now().strftime("%Y%m%d-%H%M%S")

        self.logdir = f"out/logs/MuZero/{self.neural_net.architecture}/" + run_name
        self.file_writer = tf.summary.create_file_writer(self.logdir + "/metrics")
        self.file_writer.set_as_default()

        self.return_forward_observations = (neural_net.net_args.dynamics_penalty > 0 or args.latent_decoder)
        self.observation_stack_length = neural_net.net_args.observation_length  # Readability variable

    def buildHypotheticalSteps(self, history: GameHistory, t: int, k: int) -> \
            typing.Tuple[np.ndarray, typing.Tuple[np.ndarray, np.ndarray, np.ndarray], np.ndarray]:
        """

        :param history:
        :param t:
        :param k:
        :return:
        """
        # One hot encode actions.
        actions = history.actions[t:t+k]
        a_truncation = k - len(actions)
        if a_truncation > 0:  # Uniform policy when unrolling beyond terminal states.
            actions += np.random.randint(self.game.getActionSize(), size=a_truncation).tolist()

        enc_actions = np.zeros([k, self.game.getActionSize()])
        enc_actions[np.arange(len(actions)), actions] = 1

        # Value targets.
        pis = history.probabilities[t:t+k+1]
        vs = history.observed_returns[t:t+k+1]
        rewards = history.rewards[t:t+k+1]

        # Handle truncations > 0 due to terminal states. Treat last state as absorbing state
        t_truncation = (k + 1) - len(pis)  # Target truncation due to terminal state
        if t_truncation > 0:
            pis += [pis[-1]] * t_truncation          # Zero vector
            rewards += [rewards[-1]] * t_truncation  # = 0
            vs += [0] * t_truncation                 # = 0

        obs_trajectory = []
        if self.return_forward_observations:
            obs_trajectory = [history.stackObservations(self.observation_stack_length, t=t+i+1) for i in range(k)]

        # (Actions, Targets, Observations)
        return enc_actions, (np.asarray(vs), np.asarray(rewards), np.asarray(pis)), obs_trajectory

    def sampleBatch(self, histories: typing.List[GameHistory]) -> typing.List:
        """

        :param histories:
        :return:
        """
        # Generate coordinates within the replay buffer to sample from. Also generate the loss scale of said samples.
        sample_coordinates, sample_weight = sample_batch(
            list_of_histories=histories, n=self.neural_net.net_args.batch_size, prioritize=self.args.prioritize,
            alpha=self.args.prioritize_alpha, beta=self.args.prioritize_beta)

        # Construct training examples for MuZero of the form (input, action, (targets), loss_scalar)
        examples = [(
            histories[h_i].stackObservations(self.observation_stack_length, t=i),
            *self.buildHypotheticalSteps(histories[h_i], t=i, k=self.args.K),
            loss_scale
        )
            for (h_i, i), loss_scale in zip(sample_coordinates, sample_weight)
        ]

        return examples
