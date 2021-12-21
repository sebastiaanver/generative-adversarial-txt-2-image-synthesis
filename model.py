import tensorflow as tf
import tensorflow.keras.layers as tfkl


class DCGenerator(tfkl.Layer):
    def __init__(self):
        super(DCGenerator, self).__init__()
        # Compress the embedding 

        self.input_layer = tf.keras.Sequential(
            [
                tfkl.Dense(128, activation=None),
                tfkl.LeakyReLU(),
            ]
        )
        self.layer1 = tf.keras.Sequential(
            [
                tfkl.Dense(7 * 7 * 256, use_bias=False),
                tfkl.BatchNormalization(),
                tfkl.ReLU(),
                tfkl.Reshape((7, 7, 256)),
            ]
        )
        self.layer2 = tf.keras.Sequential(
            [
                tfkl.Conv2DTranspose(
                    128, (5, 5), strides=(1, 1), padding="same", use_bias=False
                ),
                tfkl.BatchNormalization(),
                tfkl.ReLU(),
            ]
        )
        self.layer3 = tf.keras.Sequential(
            [
                tfkl.Conv2DTranspose(
                    64, (5, 5), strides=(2, 2), padding="same", use_bias=False
                ),
                tfkl.BatchNormalization(),
                tfkl.ReLU(),
            ]
        )
        self.layer4 = tfkl.Conv2DTranspose(
            1, (5, 5), strides=(2, 2), padding="same", use_bias=False, activation="tanh"
        )

    def call(self, x, z):
        x = self.input_layer(x)
        x = tf.concat([z, x], 1)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        return x


class DCDiscriminator(tfkl.Layer):
    def __init__(self):
        super(DCDiscriminator, self).__init__()
        self.layer1 = tf.keras.Sequential(
            [
                tfkl.Conv2D(
                    filters=64, kernel_size=(4, 4), strides=(2, 2), padding="same"
                ),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer2 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=128, kernel_size=(4, 4), strides=(2, 2), padding="same"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer3 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=256, kernel_size=(4, 4), strides=(2, 2), padding="same"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer4 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=512, kernel_size=(4, 4), strides=(2, 2), padding="same"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )

        # Residual layer
        self.layer5 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=128, kernel_size=(1, 1), strides=(1, 1), padding="same"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer6 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=128, kernel_size=(3, 3), strides=(1, 1), padding="same"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer7 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=512, kernel_size=(3, 3), strides=(1, 1), padding="same"),
                tfkl.BatchNormalization(),
            ]

        )
        self.layer8 = tfkl.LeakyReLU(0.2)
        # TODO: maybe change 128
        self.layer9 = tf.keras.Sequential(
            [
                tfkl.Dense(128, activation=None),
                tfkl.LeakyReLU(),
            ]
        )
        self.layer10 = tf.keras.Sequential(
            [
                tfkl.Conv2D(filters=512, kernel_size=(1, 1), strides=(1, 1), padding="valid"),
                tfkl.BatchNormalization(),
                tfkl.LeakyReLU(0.2),
            ]
        )
        self.layer11 = tfkl.Conv2D(filters=1, kernel_size=(2, 2), strides=(2, 2), padding="valid")
        self.layer12 = tfkl.sigmoid()

    def call(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        out4 = self.layer4(x)
        x = self.layer5(out4)
        x = self.layer6(x)
        x = self.layer7(x)
        x = tf.add(x, out4)
        x = self.layer8(x)
        discr_out = self.layer9(x)
        net_embed = tf.expand_dims(tf.expand_dims(x, 1), 1)
        net_embed = tf.tile(net_embed, [1, 4, 4, 1])
        x = tf.concat([discr_out, net_embed], axis=3)
        x = self.layer10(x)
        x = self.layer11(x)
        out_sigmoid = self.layer12(x)
        return out_sigmoid, x


class GAN(tf.keras.Model):
    def __init__(self):
        super(GAN, self).__init__()

        self.generator = DCGenerator()
        self.discriminator = DCDiscriminator()

        # Set up optimizers for both models.
        self.generator_optimizer = tf.keras.optimizers.Adam(1e-4)
        self.discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

        self.cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=True)

    def discriminator_loss(self, actual_output, generated_output):
        real_loss = self.cross_entropy(tf.ones_like(actual_output), actual_output)
        generated_loss = self.cross_entropy(
            tf.zeros_like(generated_output), generated_output
        )
        total_loss = real_loss + generated_loss

        return total_loss

    def generator_loss(self, generated_output):
        return self.cross_entropy(tf.ones_like(generated_output), generated_output)

    def generate_sample(self):
        noise = tf.random.normal([self.config["batch_size"], self.config["noise_dim"]])
        generated_sample = self.generator(noise, training=True)
        return generated_sample

    def train_step(self, x):
        noise = tf.random.normal([self.config["batch_size"], self.config["noise_dim"]])

        with tf.GradientTape() as discriminator_tape, tf.GradientTape() as generator_tape:
            generated_samples = self.generator(noise, training=True)

            real_output = self.discriminator(x, training=True)
            fake_output = self.discriminator(generated_samples, training=True)

            discriminator_loss = self.discriminator_loss(real_output, fake_output)
            generator_loss = self.generator_loss(fake_output)

        generator_gradients = generator_tape.gradient(
            generator_loss, self.generator.trainable_variables
        )
        self.generator_optimizer.apply_gradients(
            zip(generator_gradients, self.generator.trainable_variables)
        )

        discriminator_gradients = discriminator_tape.gradient(
            discriminator_loss, self.discriminator.trainable_variables
        )
        self.discriminator_optimizer.apply_gradients(
            zip(discriminator_gradients, self.discriminator.trainable_variables)
        )

        return discriminator_loss, generator_loss

    def call(self, x):
        return self.train_step(x)