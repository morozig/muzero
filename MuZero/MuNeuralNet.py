"""

"""
import typing
import datetime

import tensorflow as tf
import numpy as np

from utils import DotDict
from utils.loss_utils import scalar_loss, scale_gradient


class MuZeroNeuralNet:
    """
    This class specifies the base NeuralNet class. To define your own neural
    network, subclass this class and implement the functions below. The neural
    network does not consider the current player, and instead only deals with
    the canonical form of the board.

    See othello/NNet.py for an example implementation.
    """

    def __init__(self, game, net_args: DotDict, builder: typing.Callable) -> None:
        """

        :param game:
        :param net_args:
        :param builder:
        """
        self.fit_rewards = (game.n_players == 1)
        self.net_args = net_args
        self.neural_net = builder(game, net_args)

        self.optimizer = tf.optimizers.Adam(self.net_args.lr)
        self.steps = 0

        self.logdir = "logs/scalars/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")  # TODO specify path in file
        self.file_writer = tf.summary.create_file_writer(self.logdir + "/metrics")
        self.file_writer.set_as_default()

    def loss_function(self, observations: tf.Tensor, actions: tf.Tensor, target_vs: tf.Tensor, target_rs: tf.Tensor,
                      target_pis: tf.Tensor, sample_weights: tf.Tensor) -> tf.function:
        """

        :param observations: Shape (batch_size, observation_dimensions)
        :param actions: Shape (batch_size, K, action_size)
        :param target_vs:
        :param target_rs:
        :param target_pis:
        :param sample_weights:
        :return:
        """
        @tf.function
        def loss() -> tf.Tensor:
            """
            Defines the computation graph for computing the loss of a MuZero model given data.

            :return: tf.Tensor with value being the total loss of the MuZero model given the data.
            """
            total_loss = tf.constant(0, dtype=tf.float32)

            # Root inference. Collect predictions of the form: [w_i / K, v, r, pi] for each forward step k = 0...K
            s, pi_0, v_0 = self.neural_net.forward(observations)
            predictions = [(sample_weights, v_0, None, pi_0)]

            for t in range(actions.shape[1]):
                s = scale_gradient(s, 1/2)  # Scale the gradient at the start of the dynamics function by 1/2
                r, s, pi, v = self.neural_net.recurrent([s[..., 0], actions[:, t, :]])

                predictions.append((tf.divide(sample_weights, len(actions)), v, r, pi))

            # Perform loss computation
            for t in range(len(predictions)):  # Length = 1 + K (root + hypothetical forward steps)
                loss_scale, vs, rs, pis = predictions[t]
                t_vs, t_rs, t_pis = target_vs[t, ...], target_rs[t, ...], target_pis[t, ...]

                r_loss = scalar_loss(rs, t_rs) if (t > 0 and self.fit_rewards) else tf.constant(0, dtype=tf.float32)
                v_loss = scalar_loss(vs, t_vs)
                pi_loss = scalar_loss(pis, t_pis)

                # Logging loss of each unrolled head.
                tf.summary.scalar(f"r_loss_{t}", data=tf.reduce_sum(r_loss * loss_scale), step=self.steps)
                tf.summary.scalar(f"v_loss_{t}", data=tf.reduce_sum(v_loss * loss_scale), step=self.steps)
                tf.summary.scalar(f"pi_loss_{t}", data=tf.reduce_sum(pi_loss * loss_scale), step=self.steps)

                step_loss = r_loss + v_loss + pi_loss
                total_loss += tf.reduce_sum(step_loss * loss_scale)

            tf.summary.scalar("loss", data=total_loss, step=self.steps)

            # Penalize magnitude of weights using l2 norm
            penalty = self.net_args.l2 * tf.reduce_sum([tf.nn.l2_loss(x) for x in self.get_variables()])
            tf.summary.scalar("l2 penalty", data=penalty, step=self.steps)

            total_loss += penalty

            return total_loss

        return loss

    def train(self, examples: typing.List) -> None:
        """
        This function trains the neural network with examples obtained from
        self-play.

        Input:
            examples: a list of training examples of the form (observation_trajectory,
                      action_trajectory, targets, loss_scale). Here targets is another
                      tuple comprised of the trajectories of (v, r, pi).
        """
        pass

    def get_variables(self) -> typing.List:
        """
        Yield a list of all trainable variables within the model

        Returns:
            variable_list: A list of all tf.Variables within the entire MuZero model.
        """
        pass

    def initial_inference(self, observations: np.ndarray) -> typing.Tuple[np.ndarray, np.ndarray, float]:
        """
        Combines the prediction and representation models into one call. This reduces
        overhead and results in a significant speed up.

        Input:
            observations: A game specific (stacked) tensor of observations of the environment at step t: o_t.

        Returns:
            s_(0): The root 'latent_state' produced by the representation function
            pi: a policy vector for the current board- a numpy array of length
                game.getActionSize
            v: a float that gives the value of the current board
        """
        pass
    
    def recurrent_inference(self, latent_state: np.ndarray, action: int) -> typing.Tuple[float, np.ndarray,
                                                                                         np.ndarray, float]:
        """
        Combines the prediction and dynamics models into one call. This reduces
        overhead and results in a significant speed up.

        Input:
            latent_state: A neural encoding of the environment at step k: s_k.
            action: A (encoded) action to perform on the latent state

        Returns:
            r: The immediate predicted reward of the environment.
            s_(k+1): A new 'latent_state' resulting from performing the 'action' in
                the latent_state.
            pi: a policy vector for the current board- a numpy array of length
                game.getActionSize.
            v: a float that gives the value of the current board.
        """
        pass

    def save_checkpoint(self, folder: str, filename: str) -> None:
        """
        Saves the current neural network (with its parameters) in
        folder/filename
        """
        pass

    def load_checkpoint(self, folder: str, filename: str) -> None:
        """
        Loads parameters of the neural network from folder/filename
        """
        pass
